"""Stage-by-stage pipeline orchestration that emits progress events.

Mirrors the flow in ``src/pipeline.py:run_pipeline`` and ``src/main.py`` so the
backend can stream stage/progress updates over SSE, while reusing all the
underlying business logic functions directly (no duplication).
"""

from __future__ import annotations

import csv
import json
import queue
import time
from pathlib import Path
from typing import Any, Callable

from src.config import Settings, load_settings
from src.enrichment import EnrichmentConfig, EnrichmentOrchestrator
from src.exporters import export_instantly_campaign
from src.ingest import read_contacts
from src.messaging import generate_sequence
from src.models import Contact, EnrichmentResult, GeneratedSequence
from src.openrouter_client import OpenRouterClient
from src.pipeline import PipelineRunReport, _get_provenance_fields
from src.prospecting import (
    ICPProfile,
    dedupe_contacts,
    discover_contacts,
    discover_referral_advocates,
    load_icp_profile,
    qualify_contact,
)
from src.schedule import suggest_send_times
from src.scoring import classify

from .ebitda import filter_by_min_ebitda


FIELDNAMES = [
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
    "title_source",
    "company_source",
    "industry_source",
    "enriched_at",
    "voice_profile_version",
    "generation_method",
    "validation_passed",
    "validation_errors",
    # Extra convenience fields for the frontend
    "subject_1",
    "subject_2",
    "subject_3",
]


EventEmitter = Callable[[str, dict[str, Any]], None]


def make_emitter(q: queue.Queue) -> EventEmitter:
    """Build an event emitter that pushes dict payloads onto a queue."""

    def emit(event: str, data: dict[str, Any]) -> None:
        q.put({"event": event, "data": data})

    return emit


def _apply_icp_overrides(
    icp: ICPProfile, overrides: dict[str, Any] | None
) -> ICPProfile:
    if not overrides:
        return icp
    data = icp.to_dict()
    data.update({k: v for k, v in overrides.items() if v is not None})
    return ICPProfile.from_dict(data)


def _extract_subject(body: str) -> str:
    if not body:
        return ""
    first_line = body.strip().splitlines()[0].strip()
    if first_line.lower().startswith("subject:"):
        return first_line.split(":", 1)[1].strip()
    return ""


def execute(
    *,
    run_id: str,
    mode: str,
    csv_paths: list[str],
    output_path: str,
    instantly_path: str,
    dry_run: bool = True,
    enrich: bool = False,
    use_master_persona: bool = True,
    master_persona_path: str = "MASTER.md",
    voice_profile_path: str = "data/voice_profile.json",
    few_shot_k: int = 3,
    min_qualification_score: int = 60,
    min_fit_score_for_enrich: int = 65,
    referral_advocates_only: bool = False,
    state: str = "CO",
    prospect_sources: list[str] | None = None,
    prospect_limit: int = 25,
    hunter_domains: list[str] | None = None,
    min_ebitda: int = 0,
    icp_overrides: dict[str, Any] | None = None,
    emit: EventEmitter,
) -> tuple[int, PipelineRunReport]:
    """Execute the pipeline with staged progress events."""
    start_time = time.time()
    report = PipelineRunReport()

    settings: Settings = load_settings()
    llm = OpenRouterClient(settings)

    icp_profile = _apply_icp_overrides(
        load_icp_profile("data/icp_profile.json"), icp_overrides
    )

    # Stage 1: Ingest (CSV + optional prospecting discovery)
    emit("stage", {"stage": "ingest"})
    seed_contacts: list[Contact] | None = None
    input_paths = list(csv_paths)

    want_discovery = mode in ("api_discovery", "csv_plus_api")
    if want_discovery:
        sources = prospect_sources or ["apollo"]
        if referral_advocates_only:
            discovered = discover_referral_advocates(
                settings=settings,
                icp_profile=icp_profile,
                state=state,
                limit=prospect_limit,
                sources=sources,
                hunter_domains=hunter_domains or [],
            )
        else:
            discovered = discover_contacts(
                settings=settings,
                icp_profile=icp_profile,
                sources=sources,
                limit=prospect_limit,
                hunter_domains=hunter_domains or [],
            )
        if input_paths:
            merged = discovered + read_contacts(input_paths)
            seed_contacts = dedupe_contacts(merged)
            input_paths = []
        else:
            seed_contacts = discovered
            input_paths = []

    contacts = (
        seed_contacts if seed_contacts is not None else read_contacts(input_paths)
    )
    report.total_contacts = len(contacts)
    emit(
        "progress",
        {"current": len(contacts), "total": len(contacts), "stage": "ingest"},
    )

    # Stage 1.5: Pre-enrichment fit filter to reduce wasted enrichment calls.
    if min_fit_score_for_enrich > 0:
        filtered_contacts: list[Contact] = []
        for contact in contacts:
            classified = classify(contact)
            if classified.fit_score >= min_fit_score_for_enrich:
                filtered_contacts.append(contact)
            else:
                report.skipped_low_fit_count += 1
        contacts = filtered_contacts

    # Stage 2: Enrich (optional)
    emit("stage", {"stage": "enrich"})
    enrichment_results: list[EnrichmentResult] = []
    if enrich and not dry_run:
        orchestrator = EnrichmentOrchestrator(
            settings,
            EnrichmentConfig(
                enable_apollo=bool(settings.apollo_api_key),
                enable_apify=bool(
                    settings.apify_api_token and settings.apify_linkedin_actor_id
                ),
            ),
        )
        total = len(contacts)
        for idx, contact in enumerate(contacts, start=1):
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
                report.enrichment_errors.append(f"{contact.row_id}: {e}")
                enrichment_results.append(
                    EnrichmentResult(
                        contact=contact,
                        sources_applied=[],
                        fields_updated=[],
                        errors=[str(e)],
                    )
                )
            emit("progress", {"current": idx, "total": total, "stage": "enrich"})
    else:
        enrichment_results = [
            EnrichmentResult(
                contact=c, sources_applied=[], fields_updated=[], errors=[]
            )
            for c in contacts
        ]
        emit(
            "progress",
            {"current": len(contacts), "total": len(contacts), "stage": "enrich"},
        )

    # Hard skip contacts with no LinkedIn after enrichment.
    linkedin_ready: list[EnrichmentResult] = []
    for result in enrichment_results:
        if (result.contact.linkedin or "").strip():
            linkedin_ready.append(result)
        else:
            report.skipped_missing_linkedin_count += 1
    enrichment_results = linkedin_ready

    # EBITDA filter (between enrichment and classification)
    if min_ebitda and min_ebitda > 0:
        before = len(enrichment_results)
        filtered_contacts = filter_by_min_ebitda(
            [r.contact for r in enrichment_results], min_ebitda
        )
        kept_ids = {id(c) for c in filtered_contacts}
        enrichment_results = [
            r for r in enrichment_results if id(r.contact) in kept_ids
        ]
        emit(
            "progress",
            {
                "current": len(enrichment_results),
                "total": before,
                "stage": "ebitda_filter",
            },
        )

    # Stage 3: Classify + Qualify
    emit("stage", {"stage": "classify"})
    classified_rows: list[tuple[EnrichmentResult, Any, Any]] = []
    total = len(enrichment_results)
    fit_scores: list[int] = []
    for idx, result in enumerate(enrichment_results, start=1):
        contact = result.contact
        classified = classify(contact)
        fit_scores.append(classified.fit_score)

        if classified.audience == "owner":
            report.owner_count += 1
            if (
                classified.fit_breakdown.get("owner_readiness", {}).get("tier", "low")
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

        classified_rows.append((result, classified, qualification))
        emit("progress", {"current": idx, "total": total, "stage": "classify"})

    # Stage 4: Generate sequences
    emit("stage", {"stage": "generate"})
    generated: list[tuple[EnrichmentResult, Any, Any, GeneratedSequence]] = []
    total = len(classified_rows)
    for idx, (result, classified, qualification) in enumerate(classified_rows, start=1):
        try:
            sequence = generate_sequence(
                classified,
                llm,
                dry_run=dry_run,
                use_master_persona=use_master_persona,
                master_persona_path=master_persona_path,
                few_shot_k=max(1, few_shot_k),
            )
        except Exception as e:
            report.generation_failures.append(f"{result.contact.row_id}: {e}")
            sequence = GeneratedSequence(
                step_1=f"[Generation failed: {e}]",
                step_2="",
                step_3="",
                voice_profile_version="error",
                generation_method="error",
                validation_passed=False,
                validation_errors=[str(e)],
            )
        generated.append((result, classified, qualification, sequence))
        emit("progress", {"current": idx, "total": total, "stage": "generate"})

    # Stage 5: Validate (review flags)
    emit("stage", {"stage": "validate"})
    for _, classified, _, sequence in generated:
        if classified.fit_score < 55 or not sequence.validation_passed:
            report.review_flagged_count += 1
    emit(
        "progress",
        {"current": len(generated), "total": len(generated), "stage": "validate"},
    )

    # Stage 6: Export CSV (+ Instantly)
    emit("stage", {"stage": "export"})
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for result, classified, qualification, sequence in generated:
            contact = result.contact
            send1, send2, send3 = suggest_send_times()
            needs_review = classified.fit_score < 55 or not sequence.validation_passed
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
                    "review_flag": "yes" if needs_review else "no",
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
                    "subject_1": sequence.subject_1
                    or _extract_subject(sequence.step_1),
                    "subject_2": sequence.subject_2
                    or _extract_subject(sequence.step_2),
                    "subject_3": sequence.subject_3
                    or _extract_subject(sequence.step_3),
                }
            )
            count += 1

    try:
        export_instantly_campaign(str(output), instantly_path)
    except Exception as e:
        # Non-fatal; frontend can surface this
        emit(
            "progress",
            {"current": 0, "total": 0, "stage": f"instantly_export_failed:{e}"},
        )

    report.processing_time_seconds = time.time() - start_time
    report.avg_fit_score = sum(fit_scores) / len(fit_scores) if fit_scores else 0
    return count, report
