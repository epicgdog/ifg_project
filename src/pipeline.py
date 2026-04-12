from __future__ import annotations

import csv
from pathlib import Path

from .ingest import read_contacts
from .messaging import generate_sequence
from .openrouter_client import OpenRouterClient
from .schedule import suggest_send_times
from .scoring import classify


def run_pipeline(
    input_paths: list[str], output_path: str, llm: OpenRouterClient, dry_run: bool
) -> int:
    contacts = read_contacts(input_paths)
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
        "email_step_1",
        "email_step_2",
        "email_step_3",
        "send_at_step_1",
        "send_at_step_2",
        "send_at_step_3",
        "review_flag",
    ]

    count = 0
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in contacts:
            item = classify(c)
            sequence = generate_sequence(item, llm, dry_run=dry_run)
            send1, send2, send3 = suggest_send_times()
            review_flag = "yes" if item.fit_score < 55 else "no"
            writer.writerow(
                {
                    "row_id": c.row_id,
                    "source_file": c.source_file,
                    "full_name": c.full_name,
                    "first_name": c.first_name,
                    "last_name": c.last_name,
                    "email": c.email,
                    "title": c.title,
                    "company": c.company,
                    "industry": c.industry,
                    "website": c.website,
                    "linkedin": c.linkedin,
                    "city": c.city,
                    "state": c.state,
                    "audience": item.audience,
                    "audience_reason": item.audience_reason,
                    "fit_score": item.fit_score,
                    "fit_reason": item.fit_reason,
                    "email_step_1": sequence["step_1"],
                    "email_step_2": sequence["step_2"],
                    "email_step_3": sequence["step_3"],
                    "send_at_step_1": send1,
                    "send_at_step_2": send2,
                    "send_at_step_3": send3,
                    "review_flag": review_flag,
                }
            )
            count += 1

    return count
