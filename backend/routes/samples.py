"""Samples endpoint — exposes up to 10 rows from out/sample_campaign.csv."""
from __future__ import annotations

import csv
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["samples"])

SAMPLE_PATH = Path("out/sample_campaign.csv")

SAMPLE_FIELDS = [
    "full_name",
    "title",
    "company",
    "audience",
    "subject_1",
    "email_step_1",
    "subject_2",
    "email_step_2",
    "subject_3",
    "email_step_3",
]


def _extract_subject(body: str) -> str:
    if not body:
        return ""
    first_line = body.strip().splitlines()[0].strip()
    if first_line.lower().startswith("subject:"):
        return first_line.split(":", 1)[1].strip()
    return ""


@router.get("/samples")
def get_samples() -> dict[str, object]:
    if not SAMPLE_PATH.exists():
        return {"samples": [], "message": "Sample file not yet generated"}

    samples: list[dict[str, str]] = []
    with open(SAMPLE_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if len(samples) >= 10:
                break
            record = {k: row.get(k, "") for k in SAMPLE_FIELDS}
            # Fallback: derive subject from email body if not in CSV
            for i in (1, 2, 3):
                s_key = f"subject_{i}"
                b_key = f"email_step_{i}"
                if not record.get(s_key):
                    record[s_key] = _extract_subject(row.get(b_key, ""))
            samples.append(record)

    return {"samples": samples}
