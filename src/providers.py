from __future__ import annotations

import json
import re
from typing import Any

import requests
from bs4 import BeautifulSoup

from .config import Settings
from .models import Contact
from .rate_limiter import APOLLO_LIMITER, APIFY_LIMITER


class ApolloProvider:
    def __init__(self, settings: Settings) -> None:
        self._key = settings.apollo_api_key
        self._base = "https://api.apollo.io/api/v1"
        self.last_status_code: int = 0
        self.last_error: str = ""

    def _clear_last_error(self) -> None:
        self.last_status_code = 0
        self.last_error = ""

    def _set_last_error(self, status_code: int, body: str, context: str) -> None:
        self.last_status_code = status_code
        trimmed = " ".join((body or "").split())[:300]
        self.last_error = (
            f"{context}: HTTP {status_code}{f' - {trimmed}' if trimmed else ''}"
        )

    @property
    def enabled(self) -> bool:
        return bool(self._key)

    def search_people(
        self,
        person_titles: list[str],
        organization_num_employees_ranges: list[str],
        q_organization_keyword_tags: list[str],
        person_locations: list[str] | None = None,
        page: int = 1,
        per_page: int = 25,
        timeout_seconds: int = 60,
    ) -> list[dict[str, str]]:
        if not self.enabled:
            self._set_last_error(0, "Apollo API key missing", "mixed_people/search")
            return []

        payload: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
            "person_titles": person_titles,
            "organization_num_employees_ranges": organization_num_employees_ranges,
            "q_organization_keyword_tags": q_organization_keyword_tags,
        }
        if person_locations:
            payload["person_locations"] = person_locations
        headers = {"x-api-key": self._key, "Content-Type": "application/json"}
        APOLLO_LIMITER.acquire()
        response = requests.post(
            f"{self._base}/mixed_people/search",
            headers=headers,
            data=json.dumps(payload),
            timeout=timeout_seconds,
        )
        if response.status_code >= 400:
            self._set_last_error(
                response.status_code,
                response.text,
                "mixed_people/search",
            )
            return []

        self._clear_last_error()

        body: dict[str, Any] = response.json()
        people = body.get("people", [])
        out: list[dict[str, str]] = []
        for person in people:
            org = person.get("organization", {}) if isinstance(person, dict) else {}
            out.append(
                {
                    "first_name": _strv(person.get("first_name")),
                    "last_name": _strv(person.get("last_name")),
                    "full_name": _strv(person.get("name")),
                    "email": _strv(person.get("email")),
                    "title": _strv(person.get("title") or person.get("job_title")),
                    "company": _strv(org.get("name")),
                    "industry": _strv(org.get("industry")),
                    "website": _strv(org.get("website_url")),
                    "linkedin": _strv(person.get("linkedin_url")),
                    "city": _strv(person.get("city")),
                    "state": _strv(person.get("state")),
                    "notes": "Sourced via Apollo search",
                    "employee_count": _strv(org.get("employee_count")),
                    "annual_revenue": _strv(org.get("annual_revenue")),
                    "apollo_person_id": _strv(person.get("id")),
                    "apollo_org_id": _strv(org.get("id")),
                }
            )
        return out

    def enrich_contact(
        self, contact: Contact, timeout_seconds: int = 60
    ) -> dict[str, str]:
        if not self.enabled:
            self._set_last_error(0, "Apollo API key missing", "people/match")
            return {}

        payload = {
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "name": contact.full_name,
            "email": contact.email,
            "organization_name": contact.company,
            "linkedin_url": contact.linkedin,
        }
        headers = {"x-api-key": self._key, "Content-Type": "application/json"}
        APOLLO_LIMITER.acquire()
        response = requests.post(
            f"{self._base}/people/match",
            headers=headers,
            data=json.dumps(payload),
            timeout=timeout_seconds,
        )

        if response.status_code >= 400:
            self._set_last_error(
                response.status_code,
                response.text,
                "people/match",
            )
            fallback = self._fallback_search_person(contact, timeout_seconds)
            if fallback:
                self._clear_last_error()
                return fallback
            return {"apollo_error": f"{response.status_code}"}

        body: dict[str, Any] = response.json()
        self._clear_last_error()
        person = body.get("person") or body.get("people", [{}])[0] or {}
        org = person.get("organization", {}) if isinstance(person, dict) else {}

        linkedin = _strv(person.get("linkedin_url")) or contact.linkedin
        if not linkedin:
            fallback = self._fallback_search_person(contact, timeout_seconds)
            if fallback:
                linkedin = fallback.get("linkedin", "")
                if not _strv(person.get("id")):
                    person["id"] = fallback.get("apollo_person_id", "")
                if not _strv(org.get("id")):
                    org["id"] = fallback.get("apollo_org_id", "")

        return {
            "email": _strv(person.get("email")),
            "title": _strv(person.get("title") or person.get("job_title")),
            "full_name": _strv(person.get("name")),
            "first_name": _strv(person.get("first_name")),
            "last_name": _strv(person.get("last_name")),
            "apollo_person_id": _strv(person.get("id")),
            "apollo_org_id": _strv(org.get("id")),
            "company": _strv(org.get("name")) or contact.company,
            "website": _strv(org.get("website_url")) or contact.website,
            "employee_count": _strv(org.get("employee_count")),
            "annual_revenue": _strv(org.get("annual_revenue")),
            "industry": _strv(org.get("industry")) or contact.industry,
            "city": _strv(person.get("city")) or contact.city,
            "state": _strv(person.get("state")) or contact.state,
            "linkedin": linkedin,
        }

    def _fallback_search_person(
        self, contact: Contact, timeout_seconds: int
    ) -> dict[str, str]:
        """Best-effort Apollo search fallback to recover LinkedIn/profile ids."""
        if not self.enabled:
            return {}

        title = (contact.title or "").strip()
        person_titles = [title] if title else []

        company_tokens = [
            tok
            for tok in re.split(r"\W+", (contact.company or "").lower())
            if len(tok) >= 4
        ][:3]
        industry_tokens = [
            tok
            for tok in re.split(r"\W+", (contact.industry or "").lower())
            if len(tok) >= 4
        ][:2]
        keyword_tags = list(dict.fromkeys(company_tokens + industry_tokens))
        if not keyword_tags:
            return {}

        try:
            candidates = self.search_people(
                person_titles=person_titles,
                organization_num_employees_ranges=[
                    "1,10",
                    "11,20",
                    "21,50",
                    "51,100",
                    "101,200",
                    "201,500",
                    "501,1000",
                ],
                q_organization_keyword_tags=keyword_tags,
                person_locations=[contact.state]
                if (contact.state or "").strip()
                else None,
                page=1,
                per_page=25,
                timeout_seconds=timeout_seconds,
            )
        except Exception:
            return {}

        best: dict[str, str] = {}
        best_score = -1
        for c in candidates:
            score = 0
            if contact.email and c.get("email", "").lower() == contact.email.lower():
                score += 10
            if (
                contact.first_name
                and c.get("first_name", "").lower() == contact.first_name.lower()
            ):
                score += 3
            if (
                contact.last_name
                and c.get("last_name", "").lower() == contact.last_name.lower()
            ):
                score += 3
            if (
                contact.company
                and contact.company.lower() in c.get("company", "").lower()
            ):
                score += 4
            if c.get("linkedin"):
                score += 2
            if score > best_score:
                best_score = score
                best = c

        if best_score < 6:
            return {}

        return {
            "email": _strv(best.get("email")) or contact.email,
            "title": _strv(best.get("title")) or contact.title,
            "full_name": _strv(best.get("full_name")) or contact.full_name,
            "first_name": _strv(best.get("first_name")) or contact.first_name,
            "last_name": _strv(best.get("last_name")) or contact.last_name,
            "apollo_person_id": _strv(best.get("apollo_person_id")),
            "apollo_org_id": _strv(best.get("apollo_org_id")),
            "company": _strv(best.get("company")) or contact.company,
            "website": _strv(best.get("website")) or contact.website,
            "employee_count": _strv(best.get("employee_count")),
            "annual_revenue": _strv(best.get("annual_revenue")),
            "industry": _strv(best.get("industry")) or contact.industry,
            "city": _strv(best.get("city")) or contact.city,
            "state": _strv(best.get("state")) or contact.state,
            "linkedin": _strv(best.get("linkedin")) or contact.linkedin,
        }


class ApifyLinkedInProvider:
    def __init__(self, settings: Settings) -> None:
        self._token = settings.apify_api_token
        self._actor = settings.apify_linkedin_actor_id
        self._base = "https://api.apify.com/v2"

    @property
    def enabled(self) -> bool:
        return bool(self._token and self._actor)

    def scrape_profiles(
        self, linkedin_urls: list[str], timeout_seconds: int = 120
    ) -> list[dict[str, str]]:
        if not self.enabled or not linkedin_urls:
            return []

        run_input = {
            "profileUrls": linkedin_urls,
            "scrapeCompany": True,
            "includePrivateProfiles": False,
        }
        APIFY_LIMITER.acquire()
        run = requests.post(
            f"{self._base}/acts/{self._actor}/runs",
            params={"token": self._token, "waitForFinish": 120},
            json=run_input,
            timeout=max(timeout_seconds, 120),
        )
        run.raise_for_status()
        data = run.json().get("data", {})
        dataset_id = data.get("defaultDatasetId")
        if not dataset_id:
            return []

        ds = requests.get(
            f"{self._base}/datasets/{dataset_id}/items",
            params={"token": self._token, "format": "json", "clean": "true"},
            timeout=timeout_seconds,
        )
        ds.raise_for_status()
        items = ds.json()

        out: list[dict[str, str]] = []
        for item in items:
            out.append(
                {
                    "linkedin": _strv(
                        item.get("profileUrl") or item.get("linkedinUrl")
                    ),
                    "full_name": _strv(item.get("fullName") or item.get("name")),
                    "first_name": _strv(item.get("firstName")),
                    "last_name": _strv(item.get("lastName")),
                    "title": _strv(item.get("headline")),
                    "company": _strv(item.get("companyName")),
                    "city": _strv(item.get("city")),
                    "state": _strv(item.get("state")),
                    "industry": _strv(item.get("industry")),
                    "website": _strv(item.get("companyWebsite")),
                }
            )
        return out


class HunterProvider:
    def __init__(self, settings: Settings) -> None:
        self._key = settings.hunter_api_key
        self._base = "https://api.hunter.io/v2"

    @property
    def enabled(self) -> bool:
        return bool(self._key)

    def domain_search(
        self,
        domain: str,
        limit: int = 10,
        offset: int = 0,
        timeout_seconds: int = 60,
    ) -> list[dict[str, str]]:
        if not self.enabled or not domain:
            return []

        response = requests.get(
            f"{self._base}/domain-search",
            params={
                "api_key": self._key,
                "domain": domain,
                "limit": limit,
                "offset": offset,
            },
            timeout=timeout_seconds,
        )
        if response.status_code >= 400:
            return []

        data = response.json().get("data", {})
        emails = data.get("emails", [])
        out: list[dict[str, str]] = []
        for item in emails:
            out.append(
                {
                    "first_name": _strv(item.get("first_name")),
                    "last_name": _strv(item.get("last_name")),
                    "full_name": " ".join(
                        [
                            _strv(item.get("first_name")),
                            _strv(item.get("last_name")),
                        ]
                    ).strip(),
                    "email": _strv(item.get("value")),
                    "title": _strv(item.get("position")),
                    "company": _strv(data.get("organization")),
                    "industry": "",
                    "website": f"https://{domain}",
                    "linkedin": _strv(item.get("linkedin")),
                    "city": _strv(item.get("city")),
                    "state": _strv(item.get("state")),
                    "notes": "Sourced via Hunter domain search",
                    "employee_count": "",
                    "annual_revenue": "",
                    "apollo_person_id": "",
                    "apollo_org_id": "",
                }
            )
        return out


def _strv(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_domain(url: str) -> str:
    """Extract domain from URL, handling various formats."""
    from urllib.parse import urlparse
    
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.lower()
    except Exception:
        return url.lower()


class SerperProvider:
    """Serper.dev API provider for web search-based discovery."""
    
    def __init__(self, settings: Settings) -> None:
        self._key = settings.serper_api_key
        self._base = "https://google.serper.dev"
        self.last_status_code: int = 0
        self.last_error: str = ""
    
    def _clear_last_error(self) -> None:
        self.last_status_code = 0
        self.last_error = ""
    
    def _set_last_error(self, status_code: int, body: str, context: str) -> None:
        self.last_status_code = status_code
        trimmed = " ".join((body or "").split())[:300]
        self.last_error = (
            f"{context}: HTTP {status_code}{f' - {trimmed}' if trimmed else ''}"
        )
    
    @property
    def enabled(self) -> bool:
        return bool(self._key)
    
    def search(
        self,
        query: str,
        num: int = 10,
        page: int = 1,
        country: str | None = None,
        language: str | None = None,
        location: str | None = None,
    ) -> dict:
        """Generic search via Serper.dev Google API."""
        if not self.enabled:
            self._set_last_error(0, "Serper API key missing", "search")
            return {}
        
        payload: dict[str, Any] = {
            "q": query,
            "num": min(num, 100),
            "page": page,
        }
        if country:
            payload["gl"] = country
        if language:
            payload["hl"] = language
        if location:
            payload["location"] = location
        
        headers = {"X-API-KEY": self._key, "Content-Type": "application/json"}
        
        try:
            response = requests.post(
                f"{self._base}/search",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if response.status_code >= 400:
                self._set_last_error(
                    response.status_code,
                    response.text,
                    "search",
                )
                return {}
            
            self._clear_last_error()
            return response.json()
        except Exception as e:
            self._set_last_error(0, str(e), "search")
            return {}
    
    def search_companies(
        self,
        industry: str,
        location: str,
        num: int = 100,
    ) -> list[dict]:
        """Find companies by industry and location using Google search."""
        if not self.enabled:
            self._set_last_error(0, "Serper API key missing", "search_companies")
            return []
        
        query = f'"{industry}" company "{location}" "about us" OR "team"'
        
        result = self.search(query=query, num=min(num, 100))
        if not result:
            return []
        
        companies: list[dict] = []
        organic = result.get("organic", [])
        
        for item in organic:
            title = _strv(item.get("title"))
            link = _strv(item.get("link"))
            snippet = _strv(item.get("snippet"))
            
            if not link:
                continue
            
            domain = _extract_domain(link)
            company_name = title.split("|")[0].split("-")[0].strip()
            
            companies.append({
                "name": company_name,
                "website": link,
                "domain": domain,
                "description": snippet,
                "source": "serper",
            })
        
        knowledge_graph = result.get("knowledgeGraph", {})
        if knowledge_graph:
            kg_title = _strv(knowledge_graph.get("title"))
            kg_website = _strv(knowledge_graph.get("website"))
            if kg_title and kg_website:
                companies.insert(0, {
                    "name": kg_title,
                    "website": kg_website,
                    "domain": _extract_domain(kg_website),
                    "description": _strv(knowledge_graph.get("description")),
                    "source": "serper",
                })
        
        return companies
    
    def search_linkedin_profiles(
        self,
        title: str,
        location: str | None = None,
        company: str | None = None,
        num: int = 50,
    ) -> list[dict]:
        """Discover LinkedIn profiles matching criteria."""
        if not self.enabled:
            self._set_last_error(0, "Serper API key missing", "search_linkedin_profiles")
            return []
        
        query_parts = [f'site:linkedin.com/in "{title}"']
        if company:
            query_parts.append(f'"{company}"')
        if location:
            query_parts.append(f'"{location}"')
        
        query = " ".join(query_parts)
        
        result = self.search(query=query, num=min(num, 100))
        if not result:
            return []
        
        profiles: list[dict] = []
        organic = result.get("organic", [])
        
        for item in organic:
            title_text = _strv(item.get("title"))
            link = _strv(item.get("link"))
            snippet = _strv(item.get("snippet"))
            
            if not link or "linkedin.com/in/" not in link:
                continue
            
            name_parts = title_text.split("-")[0].strip().split(" ")
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            
            title_match = re.search(r"-\s*([^|]+)", title_text)
            profile_title = title_match.group(1).strip() if title_match else ""
            
            company_match = re.search(r"at\s+([^|]+)", snippet)
            company_name = company_match.group(1).strip() if company_match else ""
            
            profiles.append({
                "first_name": first_name,
                "last_name": last_name,
                "full_name": f"{first_name} {last_name}".strip(),
                "title": profile_title,
                "company": company_name,
                "linkedin": link,
                "website": "",
                "source": "serper",
            })
        
        return profiles
    
    def search_decision_makers(
        self,
        company_name: str,
        titles: list[str],
        location: str | None = None,
    ) -> list[dict]:
        """Find specific roles at a company."""
        if not self.enabled:
            self._set_last_error(0, "Serper API key missing", "search_decision_makers")
            return []
        
        results: list[dict] = []
        
        for title in titles:
            query_parts = [
                f'site:linkedin.com/in "{title}"',
                f'"{company_name}"',
            ]
            if location:
                query_parts.append(f'"{location}"')
            
            query = " ".join(query_parts)
            result = self.search(query=query, num=20)
            
            if not result:
                continue
            
            organic = result.get("organic", [])
            for item in organic:
                title_text = _strv(item.get("title"))
                link = _strv(item.get("link"))
                snippet = _strv(item.get("snippet"))
                
                if not link or "linkedin.com/in/" not in link:
                    continue
                
                name_parts = title_text.split("-")[0].strip().split(" ")
                first_name = name_parts[0] if name_parts else ""
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                
                title_match = re.search(r"-\s*([^|]+)", title_text)
                profile_title = title_match.group(1).strip() if title_match else title
                
                results.append({
                    "first_name": first_name,
                    "last_name": last_name,
                    "full_name": f"{first_name} {last_name}".strip(),
                    "title": profile_title,
                    "company": company_name,
                    "linkedin": link,
                    "website": "",
                    "source": "serper",
                })
        
        seen = set()
        unique_results: list[dict] = []
        for r in results:
            key = (r.get("full_name"), r.get("company"))
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        return unique_results
    
    def extract_company_info(self, company_name: str) -> dict:
        """Get company details from knowledge graph."""
        if not self.enabled:
            self._set_last_error(0, "Serper API key missing", "extract_company_info")
            return {}
        
        query = f'"{company_name}" company'
        result = self.search(query=query, num=10)
        
        if not result:
            return {}
        
        knowledge_graph = result.get("knowledgeGraph", {})
        if knowledge_graph:
            return {
                "name": _strv(knowledge_graph.get("title")),
                "website": _strv(knowledge_graph.get("website")),
                "description": _strv(knowledge_graph.get("description")),
                "industry": _strv(knowledge_graph.get("attributes", {}).get("Industry")),
                "headquarters": _strv(knowledge_graph.get("attributes", {}).get("Headquarters")),
                "founded": _strv(knowledge_graph.get("attributes", {}).get("Founded")),
                "employees": _strv(knowledge_graph.get("attributes", {}).get("Employees")),
                "source": "serper",
            }
        
        organic = result.get("organic", [])
        if organic:
            first = organic[0]
            return {
                "name": company_name,
                "website": _strv(first.get("link")),
                "description": _strv(first.get("snippet")),
                "industry": "",
                "headquarters": "",
                "founded": "",
                "employees": "",
                "source": "serper",
            }
        
        return {}


class WebsiteResearchProvider:
    """Scrape company websites for context and decision-maker info."""
    
    def __init__(self, settings: Settings) -> None:
        # No API key needed for basic scraping
        self._timeout = 30
        self.last_error = ""
    
    def _set_error(self, message: str) -> None:
        self.last_error = message
    
    def _clear_error(self) -> None:
        self.last_error = ""
    
    def _fetch_page(self, url: str) -> str:
        """Fetch page content with error handling."""
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            response = requests.get(url, headers=headers, timeout=self._timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self._set_error(f"Failed to fetch {url}: {str(e)}")
            return ""
    
    def scrape_company_page(self, url: str) -> dict:
        """Extract company description, team info from website."""
        self._clear_error()
        
        html = self._fetch_page(url)
        if not html:
            return {}
        
        soup = BeautifulSoup(html, "html.parser")
        domain = _extract_domain(url)
        
        # Extract meta description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = _strv(meta_tag.get("content"))
        
        if not meta_desc:
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc:
                meta_desc = _strv(og_desc.get("content"))
        
        # Extract about page content
        about_content = ""
        about_patterns = ["about", "about-us", "aboutus", "company", "who-we-are"]
        for pattern in about_patterns:
            about_link = soup.find("a", href=re.compile(pattern, re.I))
            if about_link:
                href = about_link.get("href")
                if href:
                    if href.startswith("/"):
                        about_url = f"https://{domain}{href}"
                    elif not href.startswith("http"):
                        about_url = f"https://{domain}/{href}"
                    else:
                        about_url = href
                    
                    about_html = self._fetch_page(about_url)
                    if about_html:
                        about_soup = BeautifulSoup(about_html, "html.parser")
                        for tag in about_soup.find_all(["script", "style", "nav", "footer"]):
                            tag.decompose()
                        text = about_soup.get_text(separator=" ", strip=True)
                        about_content = text[:500]
                        break
        
        # If no about page, use main content
        if not about_content:
            for tag in soup.find_all(["script", "style", "nav", "footer"]):
                tag.decompose()
            main = soup.find("main") or soup.find("div", class_=re.compile("content|main", re.I))
            if main:
                about_content = main.get_text(separator=" ", strip=True)[:500]
            else:
                about_content = soup.get_text(separator=" ", strip=True)[:500]
        
        # Extract team info
        team = self.extract_team_members(html, domain)
        
        return {
            "domain": domain,
            "website": url if url.startswith("http") else f"https://{url}",
            "meta_description": meta_desc,
            "about_content": about_content,
            "team_members": team,
        }
    
    def extract_team_members(self, html: str, domain: str) -> list[dict]:
        """Parse leadership/team pages for member info."""
        self._clear_error()
        
        soup = BeautifulSoup(html, "html.parser")
        members: list[dict] = []
        
        # Look for team/leadership sections
        team_patterns = [
            re.compile(r"team|leadership|executives|management|founders", re.I),
        ]
        
        for pattern in team_patterns:
            sections = soup.find_all(["section", "div"], class_=pattern)
            if not sections:
                sections = soup.find_all(id=pattern)
            
            for section in sections:
                cards = section.find_all(["div", "article"], class_=re.compile(r"member|person|team|card", re.I))
                if not cards:
                    cards = section.find_all("li")
                
                for card in cards:
                    name = ""
                    title = ""
                    
                    # Try to find name
                    name_elem = card.find(["h2", "h3", "h4", "strong", "span"], class_=re.compile(r"name|title", re.I))
                    if not name_elem:
                        name_elem = card.find("h3") or card.find("h2")
                    if name_elem:
                        name = _strv(name_elem.get_text())
                    
                    # Try to find title/role
                    title_elem = card.find(["span", "p", "div"], class_=re.compile(r"role|position|title|job", re.I))
                    if title_elem:
                        title = _strv(title_elem.get_text())
                    elif name_elem:
                        next_elem = name_elem.find_next_sibling()
                        if next_elem:
                            title = _strv(next_elem.get_text())
                    
                    if name and len(name) > 1 and len(name) < 100:
                        name_parts = name.split(" ")
                        members.append({
                            "first_name": name_parts[0],
                            "last_name": " ".join(name_parts[1:]),
                            "full_name": name,
                            "title": title,
                            "domain": domain,
                        })
        
        return members
    
    def find_decision_maker(self, domain: str, titles: list[str]) -> dict | None:
        """Hunt for specific roles at a company."""
        self._clear_error()
        
        if not domain.startswith(("http://", "https://")):
            url = f"https://{domain}"
        else:
            url = domain
        
        # Try team/leadership pages first
        team_paths = ["/team", "/leadership", "/about", "/company", "/executives", "/management"]
        
        for path in team_paths:
            page_url = url.rstrip("/") + path
            html = self._fetch_page(page_url)
            if not html:
                continue
            
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            
            for target_title in titles:
                pattern = re.compile(rf"\b{re.escape(target_title)}\b", re.I)
                if pattern.search(text):
                    # Found a match, extract team members and find the specific one
                    members = self.extract_team_members(html, _extract_domain(domain))
                    for member in members:
                        if pattern.search(member.get("title", "")):
                            return member
        
        # Fallback: scrape main page
        html = self._fetch_page(url)
        if html:
            members = self.extract_team_members(html, _extract_domain(domain))
            for member in members:
                for target_title in titles:
                    if target_title.lower() in member.get("title", "").lower():
                        return member
        
        return None
    
    def get_company_summary(self, domain: str) -> str:
        """Get concise company description from website."""
        self._clear_error()
        
        info = self.scrape_company_page(domain)
        if not info:
            return ""
        
        parts = []
        if info.get("meta_description"):
            parts.append(info["meta_description"])
        if info.get("about_content"):
            parts.append(info["about_content"][:300])
        
        summary = " ".join(parts)
        return summary[:500].strip()
