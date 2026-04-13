from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_settings
from .enrichment import EnrichmentConfig
from .exporters import export_instantly_campaign
from .openrouter_client import OpenRouterClient
from .pipeline import run_pipeline
from .prospecting import (
    discover_contacts,
    discover_referral_advocates,
    load_icp_profile,
)
from .voice_profile import get_voice_profile


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ForgeReach V1 outbound pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic run with dry-run (no API calls)
  python -m src.main --input data/sample.csv --output out/campaign.csv --dry-run

  # Run with live enrichment from Apollo and Apify
  python -m src.main --input data/sample.csv --output out/campaign.csv --enrich

  # Run with specific enrichment options
  python -m src.main --input data/sample.csv --output out/campaign.csv \\
      --enrich --enrich-timeout 90 --no-enrich-cache
        """.strip(),
    )

    # Core arguments
    parser.add_argument(
        "--input",
        nargs="+",
        default=[],
        help="One or more input CSV files",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output CSV path",
    )

    prospecting_group = parser.add_argument_group("Prospecting Options")
    prospecting_group.add_argument(
        "--prospect",
        action="store_true",
        help="Discover net-new contacts from configured APIs (Apollo/Hunter)",
    )
    prospecting_group.add_argument(
        "--prospect-referral-advocates",
        action="store_true",
        help="Referral-advocate-only discovery flow (API only)",
    )
    prospecting_group.add_argument(
        "--prospect-source",
        nargs="+",
        default=["apollo"],
        choices=["apollo", "hunter"],
        help="Prospecting source(s) to use (default: apollo)",
    )
    prospecting_group.add_argument(
        "--prospect-limit",
        type=int,
        default=25,
        help="Max number of discovered contacts to include (default: 25)",
    )
    prospecting_group.add_argument(
        "--hunter-domain",
        nargs="*",
        default=[],
        help="Optional domains for Hunter discovery (e.g., acme.com)",
    )
    prospecting_group.add_argument(
        "--state",
        type=str,
        default="CO",
        help="State filter for referral advocate discovery (default: CO)",
    )

    # Dry run mode
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip OpenRouter calls and use deterministic placeholder emails",
    )

    # Enrichment options
    enrichment_group = parser.add_argument_group("Enrichment Options")
    enrichment_group.add_argument(
        "--enrich",
        action="store_true",
        help="Enable API enrichment (Apollo, Apify) before scoring",
    )
    enrichment_group.add_argument(
        "--no-enrich-cache",
        dest="enrich_cache",
        action="store_false",
        default=True,
        help="Disable enrichment caching",
    )
    enrichment_group.add_argument(
        "--enrich-cache-ttl",
        type=int,
        default=24,
        help="Cache TTL in hours (default: 24)",
    )
    enrichment_group.add_argument(
        "--enrich-timeout",
        type=int,
        default=60,
        help="API timeout in seconds per provider (default: 60)",
    )
    enrichment_group.add_argument(
        "--enrich-retries",
        type=int,
        default=3,
        help="Max retries per API call (default: 3)",
    )
    enrichment_group.add_argument(
        "--clear-enrich-cache",
        action="store_true",
        help="Clear the enrichment cache before running",
    )

    # Voice profile options
    voice_group = parser.add_argument_group("Voice Profile Options")
    voice_group.add_argument(
        "--voice-profile",
        type=str,
        help="Path to voice profile JSON file (default: data/voice_profile.json)",
    )
    voice_group.add_argument(
        "--master-persona-path",
        type=str,
        default="MASTER.md",
        help="Path to master persona markdown (default: MASTER.md)",
    )
    voice_group.add_argument(
        "--disable-master-persona",
        action="store_true",
        help="Disable MASTER persona few-shot prompting",
    )
    voice_group.add_argument(
        "--few-shot-k",
        type=int,
        default=3,
        help="Number of few-shot examples per step (default: 3)",
    )

    qualification_group = parser.add_argument_group("Qualification Options")
    qualification_group.add_argument(
        "--icp-profile",
        type=str,
        default="data/icp_profile.json",
        help="Path to ICP profile JSON file (default: data/icp_profile.json)",
    )
    qualification_group.add_argument(
        "--min-qualification-score",
        type=int,
        default=60,
        help="Minimum score to mark contact qualified (default: 60)",
    )
    qualification_group.add_argument(
        "--min-fit-score-for-enrich",
        type=int,
        default=65,
        help="Minimum fit score to proceed to enrichment (default: 65; set 0 to disable filtering)",
    )
    qualification_group.add_argument(
        "--research",
        action="store_true",
        help="Enable agentic research stage before enrichment",
    )
    qualification_group.add_argument(
        "--research-depth",
        type=str,
        default="standard",
        choices=["minimal", "standard", "deep"],
        help="Research depth for agentic stage (default: standard)",
    )
    qualification_group.add_argument(
        "--no-require-verified-email",
        dest="require_verified_email",
        action="store_false",
        default=True,
        help="Disable verified-email requirement in quality gate",
    )
    qualification_group.add_argument(
        "--no-require-identity",
        dest="require_identity_confirmation",
        action="store_false",
        default=True,
        help="Disable identity requirement (linkedin or decision-maker) in quality gate",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--report",
        type=str,
        help="Write run report JSON to this path",
    )
    output_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose output including validation warnings",
    )
    output_group.add_argument(
        "--instantly-output",
        type=str,
        help="Optional path to also export Instantly-formatted CSV",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    # Load settings and initialize LLM client
    settings = load_settings()
    llm = OpenRouterClient(settings)

    if not args.input and not args.prospect and not args.prospect_referral_advocates:
        print(
            "Pipeline failed: provide --input CSV(s) or use --prospect/--prospect-referral-advocates",
            file=sys.stderr,
        )
        return 1

    # Handle cache clearing
    if args.clear_enrich_cache:
        from .enrichment import EnrichmentCache

        cache = EnrichmentCache()
        cache.clear()
        print("Enrichment cache cleared.")

    # Build enrichment config if enabled
    enrichment_config = None
    if args.enrich:
        enrichment_config = EnrichmentConfig(
            enable_apollo=bool(settings.apollo_api_key),
            enable_apify=bool(
                settings.apify_api_token and settings.apify_linkedin_actor_id
            ),
            cache_enabled=args.enrich_cache,
            cache_ttl_hours=args.enrich_cache_ttl,
            timeout_seconds=args.enrich_timeout,
            max_retries=args.enrich_retries,
        )

        if args.verbose:
            print(f"Enrichment enabled:")
            print(
                f"  - Apollo: {'enabled' if enrichment_config.enable_apollo else 'disabled (no API key)'}"
            )
            print(
                f"  - Apify: {'enabled' if enrichment_config.enable_apify else 'disabled (no token/actor)'}"
            )
            print(
                f"  - Cache: {'enabled' if enrichment_config.cache_enabled else 'disabled'}"
            )

    profile_path = args.voice_profile or "data/voice_profile.json"
    get_voice_profile(profile_path)
    if args.verbose:
        print(f"Loaded voice profile: {profile_path}")

    icp_profile = load_icp_profile(args.icp_profile)
    if args.verbose:
        print(f"Loaded ICP profile: {args.icp_profile}")

    seed_contacts = None
    input_paths = list(args.input)
    if args.prospect_referral_advocates:
        discovered = discover_referral_advocates(
            settings=settings,
            icp_profile=icp_profile,
            state=args.state,
            limit=args.prospect_limit,
            sources=args.prospect_source,
            hunter_domains=args.hunter_domain,
            timeout_seconds=args.enrich_timeout,
        )
        seed_contacts = discovered
        if args.verbose:
            print(
                f"Referral advocate discovery found {len(discovered)} contacts in {args.state.upper()}"
            )

        if input_paths:
            from .ingest import read_contacts
            from .prospecting import dedupe_contacts

            merged_contacts = discovered + read_contacts(input_paths)
            seed_contacts = dedupe_contacts(merged_contacts)
            if args.verbose:
                print(
                    f"Merged discovered + CSV contacts: {len(seed_contacts)} unique total"
                )

        input_paths = []
    elif args.prospect:
        discovered = discover_contacts(
            settings=settings,
            icp_profile=icp_profile,
            sources=args.prospect_source,
            limit=args.prospect_limit,
            hunter_domains=args.hunter_domain,
            timeout_seconds=args.enrich_timeout,
        )
        seed_contacts = discovered
        if args.verbose:
            print(
                f"Prospecting discovered {len(discovered)} contacts from {', '.join(args.prospect_source)}"
            )

        if input_paths:
            from .ingest import read_contacts
            from .prospecting import dedupe_contacts

            merged_contacts = discovered + read_contacts(input_paths)
            seed_contacts = dedupe_contacts(merged_contacts)
            if args.verbose:
                print(
                    f"Merged discovered + CSV contacts: {len(seed_contacts)} unique total"
                )

        input_paths = []

    # Run pipeline
    try:
        count, report = run_pipeline(
            input_paths=input_paths,
            output_path=args.output,
            llm=llm,
            dry_run=args.dry_run,
            enrich=args.enrich,
            enrichment_config=enrichment_config,
            icp_profile=icp_profile,
            min_qualification_score=args.min_qualification_score,
            min_fit_score_for_enrich=args.min_fit_score_for_enrich,
            research=args.research,
            research_depth=args.research_depth,
            require_verified_email=args.require_verified_email,
            require_identity_confirmation=args.require_identity_confirmation,
            seed_contacts=seed_contacts,
            use_master_persona=not args.disable_master_persona,
            master_persona_path=args.master_persona_path,
            few_shot_k=max(1, args.few_shot_k),
        )

        # Output summary
        print(f"Wrote {count} contacts to {args.output}")

        if args.verbose:
            print(f"\nRun Report:")
            for key, value in report.to_dict().items():
                print(f"  {key}: {value}")

        # Write report if requested
        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
            print(f"Report written to {args.report}")

        if args.instantly_output:
            export_path = export_instantly_campaign(args.output, args.instantly_output)
            print(f"Instantly CSV written to {export_path}")

        # Exit with warning if there were issues
        if report.generation_failures or report.enrichment_errors:
            print(f"\nWarnings:")
            if report.enrichment_errors:
                print(f"  - {len(report.enrichment_errors)} enrichment errors")
            if report.generation_failures:
                print(f"  - {len(report.generation_failures)} generation failures")
            return 1

        return 0

    except Exception as e:
        print(f"Pipeline failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
