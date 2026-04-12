from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Contact:
    row_id: str
    source_file: str
    first_name: str
    last_name: str
    full_name: str
    title: str
    company: str
    email: str
    industry: str
    website: str
    linkedin: str
    city: str
    state: str
    notes: str
    employee_count: str
    annual_revenue: str
    apollo_person_id: str
    apollo_org_id: str


@dataclass
class ClassifiedContact:
    contact: Contact
    audience: str
    audience_reason: str
    fit_score: int
    fit_reason: str
