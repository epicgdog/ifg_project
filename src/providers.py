from __future__ import annotations

import json
from typing import Any

import requests

from .config import Settings
from .models import Contact


class ApolloProvider:
    def __init__(self, settings: Settings) -> None:
        self._key = settings.apollo_api_key
        self._base = "https://api.apollo.io/api/v1"

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
        response = requests.post(
            f"{self._base}/mixed_people/search",
            headers=headers,
            data=json.dumps(payload),
            timeout=timeout_seconds,
        )
        if response.status_code >= 400:
            return []

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
        response = requests.post(
            f"{self._base}/people/match",
            headers=headers,
            data=json.dumps(payload),
            timeout=timeout_seconds,
        )

        if response.status_code >= 400:
            return {"apollo_error": f"{response.status_code}"}

        body: dict[str, Any] = response.json()
        person = body.get("person") or body.get("people", [{}])[0] or {}
        org = person.get("organization", {}) if isinstance(person, dict) else {}

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
            "linkedin": _strv(person.get("linkedin_url")) or contact.linkedin,
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
