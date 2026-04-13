from __future__ import annotations

import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .agentic_research import AgenticResearchOrchestrator
from .enrichment import EnrichmentConfig, EnrichmentOrchestrator
from .ingest import read_contacts
from .messaging import generate_sequence
from .models import ClassifiedContact, Contact, EnrichmentResult, GeneratedSequence
from .openrouter_client import OpenRouterClient
from .prospecting import load_icp_profile, qualify_contact
from .schedule import suggest_send_times
from .scoring import classify


@dataclass
class PipelineRunReport:
    """Report of pipeline execution metrics."""

    total_contacts: int = 0
    discovered_count: int = 0
    apollo_search_attempts: int = 0
    apollo_search_failures: int = 0
    apollo_empty_batches: int = 0
    apollo_fallback_attempts: int = 0
    apollo_fallback_successes: int = 0
    skipped_low_fit_count: int = 0
    skipped_missing_linkedin_count: int = 0  # Deprecated: keep for backward compat
    skipped_unverified_email_count: int = 0
    skipped_no_identity_count: int = 0
    enriched_count: int = 0
    enrichment_attempts: int = 0
    apify_attempts: int = 0
    apify_successes: int = 0
    apify_failures: int = 0
    apollo_enrich_successes: int = 0
    discovery_errors: list[str] = field(default_factory=list)
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

    # Agentic research metrics (new)
    research_contacts_processed: int = 0
    research_queries_serper: int = 0
    research_websites_scraped: int = 0
    research_emails_found: int = 0
    research_emails_verified: int = 0
    research_decision_makers_found: int = 0
    research_company_summaries_extracted: int = 0
    research_failures: list[str] = field(default_factory=list)

    # Audience & maturity metrics
    avg_audience_confidence: float = 0.0
    avg_company_maturity_score: float = 0.0

    # Quality gate configuration
    require_verified_email: bool = True
    require_identity_confirmation: bool = True
    quality_gate_formula: str = "verified_email && (linkedin || decision_maker_name)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_contacts": self.total_contacts,
            "discovered_count": self.discovered_count,
            "apollo_search_attempts": self.apollo_search_attempts,
            "apollo_search_failures": self.apollo_search_failures,
            "apollo_empty_batches": self.apollo_empty_batches,
            "apollo_fallback_attempts": self.apollo_fallback_attempts,
            "apollo_fallback_successes": self.apollo_fallback_successes,
            "skipped_low_fit_count": self.skipped_low_fit_count,
            "skipped_missing_linkedin_count": self.skipped_missing_linkedin_count,
            "skipped_unverified_email_count": self.skipped_unverified_email_count,
            "skipped_no_identity_count": self.skipped_no_identity_count,
            "discovery_error_count": len(self.discovery_errors),
            "enriched_count": self.enriched_count,
            "enrichment_attempts": self.enrichment_attempts,
            "apify_attempts": self.apify_attempts,
            "apify_successes": self.apify_successes,
            "apify_failures": self.apify_failures,
            "apollo_enrich_successes": self.apollo_enrich_successes,
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
            # Agentic research metrics
            "research_contacts_processed": self.research_contacts_processed,
            "research_queries_serper": self.research_queries_serper,
            "research_websites_scraped": self.research_websites_scraped,
            "research_emails_found": self.research_emails_found,
            "research_emails_verified": self.research_emails_verified,
            "research_decision_makers_found": self.research_decision_makers_found,
            "research_company_summaries_extracted": self.research_company_summaries_extracted,
            "research_failure_count": len(self.research_failures),
            # Audience & maturity metrics
            "avg_audience_confidence": round(self.avg_audience_confidence, 2),
            "avg_company_maturity_score": round(self.avg_company_maturity_score, 1),
            "require_verified_email": self.require_verified_email,
            "require_identity_confirmation": self.require_identity_confirmation,
            "quality_gate_formula": self.quality_gate_formula,
        }


def _quality_gate_formula(
    require_verified_email: bool, require_identity_confirmation: bool
) -> str:
    if require_verified_email and require_identity_confirmation:
        return "verified_email && (linkedin || decision_maker_name)"
    if require_verified_email:
        return "verified_email"
    if require_identity_confirmation:
        return "linkedin || decision_maker_name"
    return "none (quality gate disabled)"


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


def _process_contact(
    result: EnrichmentResult,
    llm: OpenRouterClient,
    dry_run: bool,
    icp_profile,
    min_qualification_score: int,
    use_master_persona: bool,
    master_persona_path: str,
    few_shot_k: int,
) -> dict[str, Any]:
    """Run classify + qualify + generate + schedule for a single contact.

    Returns a dict with the per-contact computed values; the caller is
    responsible for aggregating counters and writing rows in order.
    """
    contact = result.contact

    classified = classify(contact)

    qualification = qualify_contact(
        contact=contact,
        audience=classified.audience,
        fit_score=classified.fit_score,
        icp_profile=icp_profile,
        min_qualification_score=min_qualification_score,
        fit_breakdown=classified.fit_breakdown,
    )

    generation_error: str | None = None
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
        generation_error = f"{contact.row_id}: {str(e)}"
        sequence = GeneratedSequence(
            step_1=f"[Generation failed: {str(e)}]",
            step_2="",
            step_3="",
            subject_1="",
            subject_2="",
            subject_3="",
            voice_profile_version="error",
            generation_method="error",
            validation_passed=False,
            validation_errors=[str(e)],
        )

    send1, send2, send3 = suggest_send_times()

    return {
        "contact": contact,
        "classified": classified,
        "qualification": qualification,
        "sequence": sequence,
        "send_times": (send1, send2, send3),
        "generation_error": generation_error,
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
    min_fit_score_for_enrich: int = 65,
    research: bool = True,
    research_depth: str = "standard",
    require_verified_email: bool = True,
    require_identity_confirmation: bool = True,  # linkedin OR decision_maker_name
    seed_contacts: list[Contact] | None = None,
    use_master_persona: bool = True,
    master_persona_path: str = "MASTER.md",
    few_shot_k: int = 3,
    max_workers: int = 10,
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
        max_workers: Max threads for per-contact parallel work (classify +
            qualify + generate + schedule). Defaults to 10.

    Returns:
        Tuple of (contact_count, run_report)
    """
    start_time = time.time()
    report = PipelineRunReport()
    report.require_verified_email = require_verified_email
    report.require_identity_confirmation = require_identity_confirmation
    report.quality_gate_formula = _quality_gate_formula(
        require_verified_email, require_identity_confirmation
    )
    if icp_profile is None:
        icp_profile = load_icp_profile("data/icp_profile.json")

    # Stage 1: Ingest / seed contacts
    contacts = (
        seed_contacts if seed_contacts is not None else read_contacts(input_paths)
    )
    report.total_contacts = len(contacts)

    # Stage 1.5: Pre-enrichment filter - skip low-fit contacts to save API credits.
    # Contacts with a LinkedIn URL are kept regardless because Apify enrichment
    # is the whole point of having the URL — their current fit score is
    # untrustworthy until we hydrate their title/company data.
    if min_fit_score_for_enrich > 0:
        filtered_contacts = []
        for contact in contacts:
            if (contact.linkedin or "").strip() and enrich:
                filtered_contacts.append(contact)
                continue
            classified = classify(contact)
            if classified.fit_score >= min_fit_score_for_enrich:
                filtered_contacts.append(contact)
            else:
                report.skipped_low_fit_count += 1
        contacts = filtered_contacts

    # Stage 1.75: Agentic research (optional) — parallelized, per-contact isolated.
    if research and not dry_run and contacts:
        research_orchestrator = AgenticResearchOrchestrator(llm._settings)
        researched_contacts: list[Contact] = [None] * len(contacts)  # type: ignore[list-item]
        effective_research_workers = max(1, min(int(max_workers), len(contacts)))

        def _research_one(idx: int, contact: Contact):
            try:
                result = research_orchestrator.research_contact(
                    contact, depth=research_depth
                )
                return idx, result, None
            except Exception as e:  # pragma: no cover - isolated per-contact error
                return idx, None, f"{contact.row_id}: {str(e)}"

        if effective_research_workers == 1 or len(contacts) == 1:
            iterator = (_research_one(i, c) for i, c in enumerate(contacts))
        else:
            pool = ThreadPoolExecutor(max_workers=effective_research_workers)
            futures = [pool.submit(_research_one, i, c) for i, c in enumerate(contacts)]
            iterator = (f.result() for f in futures)

        for idx, result, error in iterator:
            report.research_contacts_processed += 1
            if error is not None or result is None:
                if error:
                    report.research_failures.append(error)
                researched_contacts[idx] = contacts[idx]
                continue

            researched_contacts[idx] = result.contact
            report.research_queries_serper += result.serper_queries_used
            report.research_websites_scraped += result.websites_scraped
            report.research_emails_found += result.emails_found

            if getattr(result.contact, "verified_email", False):
                report.research_emails_verified += 1
            if (getattr(result.contact, "decision_maker_name", "") or "").strip():
                report.research_decision_makers_found += 1
            if (getattr(result.contact, "company_summary", "") or "").strip():
                report.research_company_summaries_extracted += 1

            if result.errors:
                report.research_failures.extend(result.errors)

        if effective_research_workers > 1 and len(contacts) > 1:
            pool.shutdown(wait=True)
        contacts = researched_contacts

    # Stage 2: Enrich (optional)
    enrichment_results: list[EnrichmentResult] = []
    if enrich and not dry_run:
        if enrichment_config is None:
            enrichment_config = EnrichmentConfig()

        orchestrator = EnrichmentOrchestrator(llm._settings, enrichment_config)

        apify_enabled = enrichment_config.enable_apify and orchestrator.apify.enabled
        apollo_enabled = enrichment_config.enable_apollo and orchestrator.apollo.enabled
        for contact in contacts:
            try:
                report.enrichment_attempts += 1
                result = orchestrator.enrich(contact)
                enrichment_results.append(result)

                # Track whether Apify was actually attempted for this contact.
                # Apify fires when enabled AND the contact has a LinkedIn URL
                # (from CSV or from Apollo). We can't observe Apollo's linkedin
                # side-effect from here, so we approximate with contact.linkedin;
                # this is a floor, not a ceiling.
                had_linkedin_preenrich = bool((contact.linkedin or "").strip())
                if apify_enabled and had_linkedin_preenrich and not result.cached:
                    report.apify_attempts += 1
                    if "apify" in result.sources_applied:
                        report.apify_successes += 1
                    elif any(e.startswith("apify:") for e in result.errors):
                        report.apify_failures += 1

                if apollo_enabled and "apollo" in result.sources_applied:
                    report.apollo_enrich_successes += 1

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

    # Stage 2.5: Quality gate - verified email + identity confirmation
    if require_verified_email or require_identity_confirmation:
        contactable_results: list[EnrichmentResult] = []
        for result in enrichment_results:
            contact = result.contact
            has_verified_email = bool(
                getattr(contact, "verified_email", False)
                and getattr(contact, "email", "")
            )
            has_identity = bool(
                getattr(contact, "linkedin", "")
                or getattr(contact, "decision_maker_name", "")
            )

            email_pass = not require_verified_email or has_verified_email
            identity_pass = not require_identity_confirmation or has_identity

            if email_pass and identity_pass:
                contactable_results.append(result)
            else:
                if not email_pass:
                    report.skipped_unverified_email_count += 1
                if not identity_pass:
                    report.skipped_no_identity_count += 1
        enrichment_results = contactable_results

    # Stage 3-5: Classify, Generate, Schedule (parallel) -> Export (serial, ordered)
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
        "decision_maker_name",
        "decision_maker_title",
        "decision_maker_source",
        "company_summary",
        "research_status",
        "audience",
        "audience_confidence",
        "audience_reason",
        "fit_score",
        "company_maturity_score",
        "fit_reason",
        "fit_breakdown_json",
        "personalization_facts_json",
        "matched_signals",
        "owner_readiness_tier",
        "owner_readiness_confidence",
        "subject_1",
        "email_step_1",
        "subject_2",
        "email_step_2",
        "subject_3",
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

    # Run per-contact work in parallel, preserving the original order.
    # For dry-run or a single contact we avoid the thread pool overhead so
    # dry-run stays fast and deterministic with no scheduling variance.
    processed: list[dict[str, Any]] = [None] * len(enrichment_results)  # type: ignore[list-item]
    effective_workers = max(1, int(max_workers))

    if dry_run or len(enrichment_results) <= 1 or effective_workers == 1:
        for i, r in enumerate(enrichment_results):
            processed[i] = _process_contact(
                r,
                llm,
                dry_run,
                icp_profile,
                min_qualification_score,
                use_master_persona,
                master_persona_path,
                few_shot_k,
            )
    else:
        with ThreadPoolExecutor(max_workers=effective_workers) as pool:
            futures = {
                pool.submit(
                    _process_contact,
                    r,
                    llm,
                    dry_run,
                    icp_profile,
                    min_qualification_score,
                    use_master_persona,
                    master_persona_path,
                    few_shot_k,
                ): i
                for i, r in enumerate(enrichment_results)
            }
            for fut in futures:
                idx = futures[fut]
                processed[idx] = fut.result()

    fit_scores: list[int] = []
    audience_confidences: list[float] = []
    maturity_scores: list[int] = []
    count = 0

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in processed:
            contact: Contact = item["contact"]
            classified: ClassifiedContact = item["classified"]
            qualification = item["qualification"]
            sequence: GeneratedSequence = item["sequence"]
            send1, send2, send3 = item["send_times"]
            generation_error = item["generation_error"]

            fit_scores.append(classified.fit_score)
            audience_confidences.append(classified.audience_confidence)
            maturity_scores.append(classified.maturity_score)

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

            if qualification.is_qualified:
                report.qualified_count += 1
            if qualification.tier == "high":
                report.high_priority_count += 1

            if generation_error:
                report.generation_failures.append(generation_error)

            needs_review = classified.fit_score < 55 or not sequence.validation_passed
            review_flag = "yes" if needs_review else "no"
            if needs_review:
                report.review_flagged_count += 1

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
                    "decision_maker_name": contact.decision_maker_name,
                    "decision_maker_title": contact.decision_maker_title,
                    "decision_maker_source": contact.decision_maker_source,
                    "company_summary": contact.company_summary,
                    "research_status": contact.research_status,
                    "audience": classified.audience,
                    "audience_confidence": classified.audience_confidence,
                    "audience_reason": classified.audience_reason,
                    "fit_score": classified.fit_score,
                    "company_maturity_score": classified.maturity_score,
                    "fit_reason": classified.fit_reason,
                    "fit_breakdown_json": json.dumps(classified.fit_breakdown),
                    "personalization_facts_json": contact.personalization_facts_json,
                    "matched_signals": "; ".join(classified.matched_signals),
                    "owner_readiness_tier": qualification.owner_readiness_tier,
                    "owner_readiness_confidence": qualification.owner_readiness_confidence,
                    "subject_1": sequence.subject_1,
                    "email_step_1": sequence.step_1,
                    "subject_2": sequence.subject_2,
                    "email_step_2": sequence.step_2,
                    "subject_3": sequence.subject_3,
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
    report.avg_audience_confidence = (
        sum(audience_confidences) / len(audience_confidences)
        if audience_confidences
        else 0
    )
    report.avg_company_maturity_score = (
        sum(maturity_scores) / len(maturity_scores) if maturity_scores else 0
    )

    return count, report
