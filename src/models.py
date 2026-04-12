from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    # Enrichment metadata (RAG-ready structure)
    enrichment_sources: dict[str, Any] = field(default_factory=dict)
    enriched_at: str = ""
    data_confidence: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert contact to dictionary for serialization."""
        return {
            "row_id": self.row_id,
            "source_file": self.source_file,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "title": self.title,
            "company": self.company,
            "email": self.email,
            "industry": self.industry,
            "website": self.website,
            "linkedin": self.linkedin,
            "city": self.city,
            "state": self.state,
            "notes": self.notes,
            "employee_count": self.employee_count,
            "annual_revenue": self.annual_revenue,
            "apollo_person_id": self.apollo_person_id,
            "apollo_org_id": self.apollo_org_id,
            "enrichment_sources": self.enrichment_sources,
            "enriched_at": self.enriched_at,
            "data_confidence": self.data_confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Contact":
        """Create contact from dictionary."""
        return cls(
            row_id=data.get("row_id", ""),
            source_file=data.get("source_file", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            full_name=data.get("full_name", ""),
            title=data.get("title", ""),
            company=data.get("company", ""),
            email=data.get("email", ""),
            industry=data.get("industry", ""),
            website=data.get("website", ""),
            linkedin=data.get("linkedin", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            notes=data.get("notes", ""),
            employee_count=data.get("employee_count", ""),
            annual_revenue=data.get("annual_revenue", ""),
            apollo_person_id=data.get("apollo_person_id", ""),
            apollo_org_id=data.get("apollo_org_id", ""),
            enrichment_sources=data.get("enrichment_sources", {}),
            enriched_at=data.get("enriched_at", ""),
            data_confidence=data.get("data_confidence", {}),
        )


@dataclass
class ClassifiedContact:
    contact: Contact
    audience: str
    audience_reason: str
    fit_score: int
    fit_reason: str


@dataclass
class EnrichmentResult:
    """Result of enrichment operations with provenance tracking."""

    contact: Contact
    sources_applied: list[str]
    fields_updated: list[str]
    errors: list[str]
    cached: bool = False


@dataclass
class GeneratedSequence:
    """Generated email sequence with metadata."""

    step_1: str
    step_2: str
    step_3: str
    voice_profile_version: str
    generation_method: str  # "static" | "rag" (for future)
    validation_passed: bool = False
    validation_errors: list[str] = field(default_factory=list)
