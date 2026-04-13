from __future__ import annotations

import json
import re
from typing import Any

import requests

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
