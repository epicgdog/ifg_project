from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .enrichment import EnrichmentConfig, EnrichmentOrchestrator
from .ingest import read_contacts
from .messaging import generate_sequence
from .models import Contact, EnrichmentResult, GeneratedSequence
from .openrouter_client import OpenRouterClient
from .prospecting import load_icp_profile, qualify_contact
from .schedule import suggest_send_times
from .scoring import classify


@dataclass
class PipelineRunReport:
    """Report of pipeline execution metrics."""

    total_contacts: int = 0
    enriched_count: int = 0
    enrichment_errors: list[str] = field(default_factory=list)
    generation_failures: list[str] = field(default_factory=list)
    review_flagged_count: int = 0
    avg_fit_score: float = 0.0
    processing_time_seconds: float = 0.0
    cache_hits: int = 0
    qualified_count: int = 0
    high_priority_count: int = 0
    owner_count: int = 0
    referral_advocate_count: int = 0
    owner_high_readiness_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_contacts": self.total_contacts,
            "enriched_count": self.enriched_count,
            "enrichment_error_count": len(self.enrichment_errors),
            "generation_failure_count": len(self.generation_failures),
            "review_flagged_count": self.review_flagged_count,
            "avg_fit_score": round(self.avg_fit_score, 1),
            "processing_time_seconds": round(self.processing_time_seconds, 2),
            "cache_hits": self.cache_hits,
            "qualified_count": self.qualified_count,
            "high_priority_count": self.high_priority_count,
            "owner_count": self.owner_count,
            "referral_advocate_count": self.referral_advocate_count,
            "owner_high_readiness_count": self.owner_high_readiness_count,
        }


def _get_provenance_fields(contact) -> dict[str, str]:
    """Extract provenance information for CSV output."""
    if not contact.enrichment_sources:
        return {
            "title_source": "csv",
            "company_source": "csv",
            "industry_source": "csv",
            "enriched_at": "",
        }

    return {
        "title_source": contact.enrichment_sources.get("title", "csv"),
        "company_source": contact.enrichment_sources.get("company", "csv"),
        "industry_source": contact.enrichment_sources.get("industry", "csv"),
        "enriched_at": contact.enriched_at,
    }


def run_pipeline(
    input_paths: list[str],
    output_path: str,
    llm: OpenRouterClient,
    dry_run: bool = False,
    enrich: bool = False,
    enrichment_config: EnrichmentConfig | None = None,
    icp_profile=None,
    min_qualification_score: int = 60,
    seed_contacts: list[Contact] | None = None,
    use_master_persona: bool = True,
    master_persona_path: str = "MASTER.md",
    few_shot_k: int = 3,
) -> tuple[int, PipelineRunReport]:
    """
    Run the full pipeline from ingestion to output.

    Stages: ingest -> enrich (optional) -> classify -> generate -> schedule -> export

    Args:
        input_paths: List of input CSV file paths
        output_path: Output CSV file path
        llm: LLM client for generation
        dry_run: Skip API calls and use deterministic outputs
        enrich: Enable API enrichment stage
        enrichment_config: Configuration for enrichment

    Returns:
        Tuple of (contact_count, run_report)
    """
    start_time = time.time()
    report = PipelineRunReport()
    if icp_profile is None:
        icp_profile = load_icp_profile("data/icp_profile.json")

    # Stage 1: Ingest / seed contacts
    contacts = (
        seed_contacts if seed_contacts is not None else read_contacts(input_paths)
    )
    report.total_contacts = len(contacts)

    # Stage 2: Enrich (optional)
    enrichment_results: list[EnrichmentResult] = []
    if enrich and not dry_run:
        if enrichment_config is None:
            enrichment_config = EnrichmentConfig()

        orchestrator = EnrichmentOrchestrator(llm._settings, enrichment_config)

        for contact in contacts:
            try:
                result = orchestrator.enrich(contact)
                enrichment_results.append(result)

                if result.fields_updated:
                    report.enriched_count += 1
                if result.cached:
                    report.cache_hits += 1
                if result.errors:
                    report.enrichment_errors.extend(result.errors)
            except Exception as e:
                # Enrichment failure is non-fatal; continue with original contact
                report.enrichment_errors.append(f"{contact.row_id}: {str(e)}")
                enrichment_results.append(
                    EnrichmentResult(
                        contact=contact,
                        sources_applied=[],
                        fields_updated=[],
                        errors=[str(e)],
                    )
                )
    else:
        # No enrichment, wrap contacts in results
        enrichment_results = [
            EnrichmentResult(
                contact=c,
                sources_applied=[],
                fields_updated=[],
                errors=[],
            )
            for c in contacts
        ]

    # Stage 3-5: Classify, Generate, Schedule -> Export
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "row_id",
        "source_file",
        "full_name",
        "first_name",
        "last_name",
        "email",
        "title",
        "company",
        "industry",
        "website",
        "linkedin",
        "city",
        "state",
        "audience",
        "audience_reason",
        "fit_score",
        "fit_reason",
        "fit_breakdown_json",
        "matched_signals",
        "owner_readiness_tier",
        "owner_readiness_confidence",
        "email_step_1",
        "email_step_2",
        "email_step_3",
        "send_at_step_1",
        "send_at_step_2",
        "send_at_step_3",
        "review_flag",
        "qualified",
        "qualification_score",
        "qualification_tier",
        "qualification_reason",
        "qualification_breakdown_json",
        # Provenance fields
        "title_source",
        "company_source",
        "industry_source",
        "enriched_at",
        "voice_profile_version",
        "generation_method",
        "validation_passed",
        "validation_errors",
    ]

    fit_scores = []
    count = 0

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in enrichment_results:
            contact = result.contact

            # Classify
            classified = classify(contact)
            fit_scores.append(classified.fit_score)

            if classified.audience == "owner":
                report.owner_count += 1
                if (
                    classified.fit_breakdown.get("owner_readiness", {}).get(
                        "tier", "low"
                    )
                    == "high"
                ):
                    report.owner_high_readiness_count += 1
            elif classified.audience == "referral_advocate":
                report.referral_advocate_count += 1

            qualification = qualify_contact(
                contact=contact,
                audience=classified.audience,
                fit_score=classified.fit_score,
                icp_profile=icp_profile,
                min_qualification_score=min_qualification_score,
                fit_breakdown=classified.fit_breakdown,
            )

            if qualification.is_qualified:
                report.qualified_count += 1
            if qualification.tier == "high":
                report.high_priority_count += 1

            # Generate sequence
            try:
                sequence = generate_sequence(
                    classified,
                    llm,
                    dry_run=dry_run,
                    use_master_persona=use_master_persona,
                    master_persona_path=master_persona_path,
                    few_shot_k=few_shot_k,
                )
            except Exception as e:
                report.generation_failures.append(f"{contact.row_id}: {str(e)}")
                # Use fallback sequence
                sequence = GeneratedSequence(
                    step_1=f"[Generation failed: {str(e)}]",
                    step_2="",
                    step_3="",
                    voice_profile_version="error",
                    generation_method="error",
                    validation_passed=False,
                    validation_errors=[str(e)],
                )

            # Schedule
            send1, send2, send3 = suggest_send_times()

            # Review flag logic
            needs_review = classified.fit_score < 55 or not sequence.validation_passed
            review_flag = "yes" if needs_review else "no"
            if needs_review:
                report.review_flagged_count += 1

            # Provenance
            provenance = _get_provenance_fields(contact)

            writer.writerow(
                {
                    "row_id": contact.row_id,
                    "source_file": contact.source_file,
                    "full_name": contact.full_name,
                    "first_name": contact.first_name,
                    "last_name": contact.last_name,
                    "email": contact.email,
                    "title": contact.title,
                    "company": contact.company,
                    "industry": contact.industry,
                    "website": contact.website,
                    "linkedin": contact.linkedin,
                    "city": contact.city,
                    "state": contact.state,
                    "audience": classified.audience,
                    "audience_reason": classified.audience_reason,
                    "fit_score": classified.fit_score,
                    "fit_reason": classified.fit_reason,
                    "fit_breakdown_json": json.dumps(classified.fit_breakdown),
                    "matched_signals": "; ".join(classified.matched_signals),
                    "owner_readiness_tier": qualification.owner_readiness_tier,
                    "owner_readiness_confidence": qualification.owner_readiness_confidence,
                    "email_step_1": sequence.step_1,
                    "email_step_2": sequence.step_2,
                    "email_step_3": sequence.step_3,
                    "send_at_step_1": send1,
                    "send_at_step_2": send2,
                    "send_at_step_3": send3,
                    "review_flag": review_flag,
                    "qualified": "yes" if qualification.is_qualified else "no",
                    "qualification_score": qualification.score,
                    "qualification_tier": qualification.tier,
                    "qualification_reason": "; ".join(qualification.reasons),
                    "qualification_breakdown_json": json.dumps(qualification.breakdown),
                    **provenance,
                    "voice_profile_version": sequence.voice_profile_version,
                    "generation_method": sequence.generation_method,
                    "validation_passed": "yes" if sequence.validation_passed else "no",
                    "validation_errors": "; ".join(sequence.validation_errors),
                }
            )
            count += 1

    report.processing_time_seconds = time.time() - start_time
    report.avg_fit_score = sum(fit_scores) / len(fit_scores) if fit_scores else 0

    return count, report
