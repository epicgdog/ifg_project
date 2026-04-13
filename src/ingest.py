from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable

from .models import Contact


ALIASES = {
    "first_name": {
        "first_name",
        "firstname",
        "first name",
        "owner_first_name",
        "person first name",
    },
    "last_name": {
        "last_name",
        "lastname",
        "last name",
        "owner_last_name",
        "person last name",
    },
    "full_name": {
        "name",
        "full_name",
        "full name",
        "owner name",
        "contact name",
        "person name",
    },
    "title": {
        "title",
        "job_title",
        "job title",
        "role",
        "position",
        "person title",
        "person job title",
        "context",
    },
    "company": {
        "company",
        "company_name",
        "company name",
        "account",
        "account name",
        "organization",
        "organization name",
    },
    "email": {
        "email",
        "email_address",
        "work_email",
        "business email",
        "email work",
    },
    "industry": {"industry", "vertical", "sector"},
    "website": {
        "website",
        "company_website",
        "domain",
        "url",
        "organization website",
        "company domain",
    },
    "linkedin": {
        "linkedin",
        "linkedin_url",
        "linkedin profile",
        "profile_url",
        "person linkedin url",
        "linkedin url",
    },
    "city": {"city", "town"},
    "state": {"state", "province", "region"},
    "notes": {"notes", "description", "bio", "about", "audience type", "audience_type"},
    "employee_count": {
        "employee_count",
        "employees",
        "company_employee_count",
        "headcount",
    },
    "annual_revenue": {"annual_revenue", "revenue", "company_revenue"},
    "apollo_person_id": {"apollo_person_id", "person_id", "apollo id", "apollo_person"},
    "apollo_org_id": {"apollo_org_id", "organization_id", "org_id", "apollo_org"},
}


def _canon(s: str) -> str:
    normalized = s.strip().lower().replace("_", " ")
    normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _split_full_name(full_name: str) -> tuple[str, str]:
    tokens = [t for t in full_name.strip().split(" ") if t]
    if not tokens:
        return "", ""
    if len(tokens) == 1:
        return tokens[0], ""
    return tokens[0], " ".join(tokens[1:])


def _field_value(row: dict[str, str], normalized_map: dict[str, str], key: str) -> str:
    column = normalized_map.get(key)
    return (row.get(column, "") if column else "").strip()


def _normalize_headers(headers: Iterable[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for h in headers:
        c = _canon(h)
        for target, aliases in ALIASES.items():
            if c in aliases and target not in out:
                out[target] = h
    return out


def _dedupe_key(contact: Contact) -> str:
    """Stable identity key for dedup. Falls back through email → linkedin → name+company."""
    email = (contact.email or "").strip().lower()
    if email and "@" in email:
        return f"email:{email}"
    linkedin = (contact.linkedin or "").strip().lower().rstrip("/")
    if linkedin:
        return f"li:{linkedin}"
    name = (contact.full_name or f"{contact.first_name} {contact.last_name}").strip().lower()
    company = (contact.company or "").strip().lower()
    if name and company:
        return f"nc:{name}|{company}"
    return f"row:{contact.row_id}"


def _dedupe(contacts: list[Contact]) -> list[Contact]:
    seen: dict[str, Contact] = {}
    for c in contacts:
        key = _dedupe_key(c)
        existing = seen.get(key)
        if existing is None:
            seen[key] = c
            continue
        # Prefer the record with more populated fields.
        def _density(x: Contact) -> int:
            return sum(
                1
                for v in (x.email, x.linkedin, x.title, x.company, x.website, x.industry, x.city, x.state)
                if v
            )
        if _density(c) > _density(existing):
            seen[key] = c
    return list(seen.values())


def read_contacts(csv_paths: list[str]) -> list[Contact]:
    contacts: list[Contact] = []
    for path in csv_paths:
        source = Path(path).name
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                continue
            mapped = _normalize_headers(reader.fieldnames)
            for idx, row in enumerate(reader, start=1):
                first_name = _field_value(row, mapped, "first_name")
                last_name = _field_value(row, mapped, "last_name")
                full_name = _field_value(row, mapped, "full_name")
                if not full_name:
                    full_name = f"{first_name} {last_name}".strip()
                elif not first_name and not last_name:
                    first_name, last_name = _split_full_name(full_name)
                contacts.append(
                    Contact(
                        row_id=f"{source}:{idx}",
                        source_file=source,
                        first_name=first_name,
                        last_name=last_name,
                        full_name=full_name,
                        title=_field_value(row, mapped, "title"),
                        company=_field_value(row, mapped, "company"),
                        email=_field_value(row, mapped, "email"),
                        industry=_field_value(row, mapped, "industry"),
                        website=_field_value(row, mapped, "website"),
                        linkedin=_field_value(row, mapped, "linkedin"),
                        city=_field_value(row, mapped, "city"),
                        state=_field_value(row, mapped, "state"),
                        notes=_field_value(row, mapped, "notes"),
                        employee_count=_field_value(row, mapped, "employee_count"),
                        annual_revenue=_field_value(row, mapped, "annual_revenue"),
                        apollo_person_id=_field_value(row, mapped, "apollo_person_id"),
                        apollo_org_id=_field_value(row, mapped, "apollo_org_id"),
                    )
                )
    return _dedupe(contacts)
