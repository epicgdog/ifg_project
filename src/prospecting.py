from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings
from .models import Contact
from .providers import ApolloProvider, HunterProvider


@dataclass
class ICPProfile:
    name: str = "IFG Blue-Collar Growth"
    target_industry_keywords: list[str] = field(
        default_factory=lambda: [
            "roof",
            "hvac",
            "plumb",
            "electrical",
            "contractor",
            "construction",
            "industrial",
            "landscap",
            "home service",
        ]
    )
    target_owner_title_keywords: list[str] = field(
        default_factory=lambda: [
            "owner",
            "founder",
            "president",
            "ceo",
            "partner",
            "principal",
        ]
    )
    target_referral_title_keywords: list[str] = field(
        default_factory=lambda: [
            "advisor",
            "fractional cfo",
            "wealth",
            "banker",
            "broker",
            "consultant",
            "insurance",
            "eos",
            "cepa",
        ]
    )
    target_states: list[str] = field(
        default_factory=lambda: ["TX", "TN", "FL", "GA", "NC", "SC"]
    )
    excluded_keywords: list[str] = field(
        default_factory=lambda: [
            "student",
            "intern",
            "recruiter",
            "software engineer",
            "product manager",
        ]
    )
    min_employee_count: int = 5
    min_revenue: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "target_industry_keywords": self.target_industry_keywords,
            "target_owner_title_keywords": self.target_owner_title_keywords,
            "target_referral_title_keywords": self.target_referral_title_keywords,
            "target_states": self.target_states,
            "excluded_keywords": self.excluded_keywords,
            "min_employee_count": self.min_employee_count,
            "min_revenue": self.min_revenue,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ICPProfile":
        return cls(
            name=str(data.get("name", "IFG Blue-Collar Growth")),
            target_industry_keywords=[
                str(x) for x in data.get("target_industry_keywords", [])
            ],
            target_owner_title_keywords=[
                str(x) for x in data.get("target_owner_title_keywords", [])
            ],
            target_referral_title_keywords=[
                str(x) for x in data.get("target_referral_title_keywords", [])
            ],
            target_states=[str(x).upper() for x in data.get("target_states", [])],
            excluded_keywords=[str(x) for x in data.get("excluded_keywords", [])],
            min_employee_count=int(data.get("min_employee_count", 5)),
            min_revenue=int(data.get("min_revenue", 0)),
        )


@dataclass
class ProspectQualification:
    score: int
    tier: str
    reasons: list[str]
    is_qualified: bool


RA_ROLE_PRESETS: dict[str, list[str]] = {
    "wealth_manager": [
        "wealth manager",
        "wealth advisor",
        "private wealth advisor",
        "financial advisor",
    ],
    "construction_insurance_broker": [
        "construction insurance",
        "commercial lines producer",
        "risk advisor",
        "insurance broker",
    ],
    "fractional_cfo": ["fractional cfo", "outsourced cfo", "virtual cfo"],
    "eos_implementer": ["eos implementer", "implementer"],
    "cepa_advisor": ["cepa", "exit planning advisor"],
    "regional_banker": [
        "commercial banker",
        "relationship manager",
        "business banker",
        "svp commercial banking",
    ],
}


def load_icp_profile(path: str | Path) -> ICPProfile:
    profile_path = Path(path)
    if not profile_path.exists():
        profile = ICPProfile()
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)
        return profile

    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ICPProfile.from_dict(data)


def get_ra_role_titles(role_keys: list[str] | None = None) -> list[str]:
    keys = role_keys or list(RA_ROLE_PRESETS.keys())
    titles: list[str] = []
    for key in keys:
        titles.extend(RA_ROLE_PRESETS.get(key, []))

    seen: set[str] = set()
    deduped: list[str] = []
    for title in titles:
        t = title.strip().lower()
        if t and t not in seen:
            seen.add(t)
            deduped.append(title)
    return deduped


def _to_contact(record: dict[str, str], source: str, index: int) -> Contact:
    first = record.get("first_name", "").strip()
    last = record.get("last_name", "").strip()
    full_name = record.get("full_name", "").strip() or f"{first} {last}".strip()
    return Contact(
        row_id=f"{source}:{index}",
        source_file=source,
        first_name=first,
        last_name=last,
        full_name=full_name,
        title=record.get("title", "").strip(),
        company=record.get("company", "").strip(),
        email=record.get("email", "").strip(),
        industry=record.get("industry", "").strip(),
        website=record.get("website", "").strip(),
        linkedin=record.get("linkedin", "").strip(),
        city=record.get("city", "").strip(),
        state=record.get("state", "").strip(),
        notes=record.get("notes", "").strip(),
        employee_count=record.get("employee_count", "").strip(),
        annual_revenue=record.get("annual_revenue", "").strip(),
        apollo_person_id=record.get("apollo_person_id", "").strip(),
        apollo_org_id=record.get("apollo_org_id", "").strip(),
    )


def dedupe_contacts(contacts: list[Contact]) -> list[Contact]:
    seen: set[str] = set()
    out: list[Contact] = []
    for contact in contacts:
        key = (
            contact.email.lower().strip()
            or contact.linkedin.lower().strip()
            or f"{contact.full_name.lower().strip()}|{contact.company.lower().strip()}"
        )
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(contact)
    return out


def _contains_any(text: str, hints: list[str]) -> bool:
    t = text.lower()
    return any(h.lower() in t for h in hints)


def _parse_int(value: str) -> int:
    if not value:
        return 0
    digits = re.sub(r"[^0-9]", "", value)
    if not digits:
        return 0
    return int(digits)


def _employee_ranges_for_min(min_employees: int) -> list[str]:
    ranges = ["1,10", "11,20", "21,50", "51,100", "101,200", "201,500", "501,1000"]
    if min_employees <= 1:
        return ranges
    filtered: list[str] = []
    for item in ranges:
        low = int(item.split(",", maxsplit=1)[0])
        high = int(item.split(",", maxsplit=1)[1])
        if low >= min_employees or high >= min_employees:
            filtered.append(item)
    return filtered or ranges


def discover_contacts(
    settings: Settings,
    icp_profile: ICPProfile,
    sources: list[str],
    limit: int,
    hunter_domains: list[str] | None = None,
    timeout_seconds: int = 60,
) -> list[Contact]:
    normalized_sources = {s.strip().lower() for s in sources if s.strip()}
    contacts: list[Contact] = []
    index = 1

    if "apollo" in normalized_sources:
        apollo = ApolloProvider(settings)
        if apollo.enabled:
            titles = list(
                dict.fromkeys(
                    icp_profile.target_owner_title_keywords
                    + icp_profile.target_referral_title_keywords
                )
            )
            keywords = icp_profile.target_industry_keywords[:10]
            employee_ranges = _employee_ranges_for_min(icp_profile.min_employee_count)

            page = 1
            while len(contacts) < limit:
                per_page = min(25, limit - len(contacts))
                batch = apollo.search_people(
                    person_titles=titles,
                    organization_num_employees_ranges=employee_ranges,
                    q_organization_keyword_tags=keywords,
                    person_locations=None,
                    page=page,
                    per_page=per_page,
                    timeout_seconds=timeout_seconds,
                )
                if not batch:
                    break

                for item in batch:
                    contacts.append(
                        _to_contact(item, source="prospect:apollo", index=index)
                    )
                    index += 1
                    if len(contacts) >= limit:
                        break

                if len(batch) < per_page:
                    break
                page += 1

    if "hunter" in normalized_sources and len(contacts) < limit:
        hunter = HunterProvider(settings)
        if hunter.enabled:
            domains = [d.strip().lower() for d in (hunter_domains or []) if d.strip()]
            if domains:
                remaining = max(0, limit - len(contacts))
                per_domain_limit = max(1, min(10, remaining // len(domains) or 1))
                for domain in domains:
                    batch = hunter.domain_search(
                        domain=domain,
                        limit=per_domain_limit,
                        offset=0,
                        timeout_seconds=timeout_seconds,
                    )
                    for item in batch:
                        contacts.append(
                            _to_contact(item, source="prospect:hunter", index=index)
                        )
                        index += 1
                        if len(contacts) >= limit:
                            break
                    if len(contacts) >= limit:
                        break

    return dedupe_contacts(contacts)[:limit]


def discover_referral_advocates(
    settings: Settings,
    icp_profile: ICPProfile,
    state: str,
    limit: int,
    role_keys: list[str] | None = None,
    sources: list[str] | None = None,
    hunter_domains: list[str] | None = None,
    timeout_seconds: int = 60,
) -> list[Contact]:
    normalized_sources = {s.strip().lower() for s in (sources or ["apollo"])}
    contacts: list[Contact] = []
    index = 1

    if "apollo" in normalized_sources:
        apollo = ApolloProvider(settings)
        if apollo.enabled:
            titles = get_ra_role_titles(role_keys)
            keywords = [
                "business owners",
                "exit planning",
                "succession",
                "blue-collar",
                "construction",
            ]
            employee_ranges = _employee_ranges_for_min(icp_profile.min_employee_count)
            page = 1

            while len(contacts) < limit:
                per_page = min(25, limit - len(contacts))
                batch = apollo.search_people(
                    person_titles=titles,
                    organization_num_employees_ranges=employee_ranges,
                    q_organization_keyword_tags=keywords,
                    person_locations=[state],
                    page=page,
                    per_page=per_page,
                    timeout_seconds=timeout_seconds,
                )
                if not batch:
                    break

                for item in batch:
                    item["notes"] = "Sourced via Apollo RA search"
                    contacts.append(
                        _to_contact(item, source="prospect:apollo_ra", index=index)
                    )
                    index += 1
                    if len(contacts) >= limit:
                        break

                if len(batch) < per_page:
                    break
                page += 1

    if "hunter" in normalized_sources and len(contacts) < limit:
        hunter = HunterProvider(settings)
        if hunter.enabled:
            domains = [d.strip().lower() for d in (hunter_domains or []) if d.strip()]
            remaining = max(0, limit - len(contacts))
            per_domain_limit = max(1, min(10, remaining // max(1, len(domains))))
            role_terms = [t.lower() for t in get_ra_role_titles(role_keys)]
            for domain in domains:
                batch = hunter.domain_search(
                    domain=domain,
                    limit=per_domain_limit,
                    offset=0,
                    timeout_seconds=timeout_seconds,
                )
                for item in batch:
                    role_text = (
                        f"{item.get('title', '')} {item.get('notes', '')}".lower()
                    )
                    if role_terms and not any(term in role_text for term in role_terms):
                        continue
                    item["notes"] = "Sourced via Hunter RA fallback"
                    contacts.append(
                        _to_contact(item, source="prospect:hunter_ra", index=index)
                    )
                    index += 1
                    if len(contacts) >= limit:
                        break
                if len(contacts) >= limit:
                    break

    for contact in contacts:
        if not contact.state:
            contact.state = state.upper()
        if not contact.notes:
            contact.notes = "Referral advocate prospect"

    return dedupe_contacts(contacts)[:limit]


def qualify_contact(
    contact: Contact,
    audience: str,
    fit_score: int,
    icp_profile: ICPProfile,
    min_qualification_score: int,
) -> ProspectQualification:
    title = contact.title.lower()
    industry = contact.industry.lower()
    notes = contact.notes.lower()
    combined = " ".join([title, industry, notes])

    score = fit_score
    reasons: list[str] = []

    if _contains_any(combined, icp_profile.target_industry_keywords):
        score += 15
        reasons.append("Industry aligns with ICP")

    if audience == "owner" and _contains_any(
        title, icp_profile.target_owner_title_keywords
    ):
        score += 10
        reasons.append("Owner/operator title match")

    if audience == "referral_advocate" and _contains_any(
        combined, icp_profile.target_referral_title_keywords
    ):
        score += 10
        reasons.append("Referral partner profile match")

    state = contact.state.upper().strip()
    if state and state in {x.upper() for x in icp_profile.target_states}:
        score += 5
        reasons.append("Target geography match")

    employees = _parse_int(contact.employee_count)
    if employees >= icp_profile.min_employee_count > 0:
        score += 5
        reasons.append("Headcount within target range")

    revenue = _parse_int(contact.annual_revenue)
    if revenue >= icp_profile.min_revenue > 0:
        score += 5
        reasons.append("Revenue within target range")

    if _contains_any(combined, icp_profile.excluded_keywords):
        score -= 20
        reasons.append("Contains excluded profile signals")

    score = max(0, min(100, score))
    if score >= 75:
        tier = "high"
    elif score >= min_qualification_score:
        tier = "medium"
    else:
        tier = "low"

    return ProspectQualification(
        score=score,
        tier=tier,
        reasons=reasons or ["Baseline fit from current profile context"],
        is_qualified=score >= min_qualification_score,
    )
