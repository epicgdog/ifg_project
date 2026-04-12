from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import load_settings
from .enrichment import EnrichmentConfig
from .openrouter_client import OpenRouterClient
from .pipeline import PipelineRunReport, run_pipeline
from .prospecting import (
    dedupe_contacts,
    discover_contacts,
    discover_referral_advocates,
    load_icp_profile,
)
from .ingest import read_contacts
from .voice_profile import get_voice_profile, reset_voice_profile


@dataclass
class DashboardRunResult:
    output_path: Path
    report: PipelineRunReport


def run_campaign_pipeline(
    input_paths: list[str],
    dry_run: bool,
    enrich: bool,
    enrich_cache: bool,
    enrich_cache_ttl: int,
    enrich_timeout: int,
    enrich_retries: int,
    voice_profile_path: str | None = None,
    icp_profile_path: str = "data/icp_profile.json",
    min_qualification_score: int = 60,
    prospect: bool = False,
    prospect_sources: list[str] | None = None,
    prospect_limit: int = 25,
    hunter_domains: list[str] | None = None,
    referral_advocates_only: bool = False,
    state: str = "CO",
) -> DashboardRunResult:
    settings = load_settings()
    llm = OpenRouterClient(settings)

    if voice_profile_path:
        reset_voice_profile()
        get_voice_profile(voice_profile_path)

    icp_profile = load_icp_profile(icp_profile_path)

    enrichment_config = None
    if enrich:
        enrichment_config = EnrichmentConfig(
            enable_apollo=bool(settings.apollo_api_key),
            enable_apify=bool(
                settings.apify_api_token and settings.apify_linkedin_actor_id
            ),
            cache_enabled=enrich_cache,
            cache_ttl_hours=enrich_cache_ttl,
            timeout_seconds=enrich_timeout,
            max_retries=enrich_retries,
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="forgereach_"))
    output_path = temp_dir / "campaign_ready.csv"

    seed_contacts = None
    if prospect:
        if referral_advocates_only:
            discovered = discover_referral_advocates(
                settings=settings,
                icp_profile=icp_profile,
                state=state,
                limit=prospect_limit,
                sources=prospect_sources or ["apollo"],
                hunter_domains=hunter_domains or [],
                timeout_seconds=enrich_timeout,
            )
        else:
            discovered = discover_contacts(
                settings=settings,
                icp_profile=icp_profile,
                sources=prospect_sources or ["apollo"],
                limit=prospect_limit,
                hunter_domains=hunter_domains or [],
                timeout_seconds=enrich_timeout,
            )
        seed_contacts = discovered
        if input_paths:
            seed_contacts = dedupe_contacts(discovered + read_contacts(input_paths))
        input_paths = []

    _, report = run_pipeline(
        input_paths=input_paths,
        output_path=str(output_path),
        llm=llm,
        dry_run=dry_run,
        enrich=enrich,
        enrichment_config=enrichment_config,
        icp_profile=icp_profile,
        min_qualification_score=min_qualification_score,
        seed_contacts=seed_contacts,
    )

    return DashboardRunResult(output_path=output_path, report=report)
