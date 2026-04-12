from __future__ import annotations

import argparse
import sys

from .config import load_settings
from .openrouter_client import OpenRouterClient
from .pipeline import run_pipeline


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ForgeReach V1 outbound pipeline")
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="One or more input CSV files",
    )
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip OpenRouter calls and use deterministic placeholder emails",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    settings = load_settings()
    llm = OpenRouterClient(settings)
    count = run_pipeline(args.input, args.output, llm=llm, dry_run=args.dry_run)
    print(f"Wrote {count} contacts to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
