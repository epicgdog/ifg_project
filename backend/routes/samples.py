"""Samples endpoint — exposes up to 10 rows from data/actual_sample.csv."""

from __future__ import annotations

import csv
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["samples"])

SAMPLE_PATH = Path("data/actual_sample.csv")

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


def _row_get(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _infer_audience(title: str) -> str:
    t = (title or "").lower()
    referral_hints = (
        "advisor",
        "wealth",
        "banker",
        "broker",
        "cpa",
        "cfp",
        "cepa",
        "fractional cfo",
        "cfo",
        "eos",
    )
    return "referral_advocate" if any(h in t for h in referral_hints) else "owner"


def _fallback_subject(step: int, company: str, audience: str) -> str:
    if audience == "referral_advocate":
        defaults = {
            1: "Comparing notes on owner transitions",
            2: "A referral pattern worth sharing",
            3: "One-page founder fit overview",
        }
        return defaults.get(step, "Comparing notes")
    company_bit = company or "your market"
    defaults = {
        1: f"Founder-to-founder intro at {company_bit}",
        2: "Two practical leverage moves",
        3: "Worth a short intro call?",
    }
    return defaults.get(step, "Quick note")


def _fallback_body(step: int, first_name: str, company: str, audience: str) -> str:
    name = first_name or "there"
    company_bit = company or "your company"
    if audience == "referral_advocate":
        if step == 1:
            return (
                f"{name}, I run IFG - we help blue-collar founders scale and exit. "
                f"Your role around owners at {company_bit} stood out, and I wanted to connect. "
                "Open to a short call to compare what founders are prioritizing this year?"
            )
        if step == 2:
            return (
                f"{name}, we often see owners wait too long to get exit-ready. "
                "We help tighten operations and story before that timing pressure hits. "
                "Would it be useful if I shared the short framework we give advisor partners?"
            )
        return (
            f"{name}, if helpful, I can send a one-page profile of founders IFG is best suited for "
            "and where we are not. Want me to send that over?"
        )

    if step == 1:
        return (
            f"{name}, I run IFG - we work with blue-collar founders on growth and exits. "
            f"I came across {company_bit} and wanted to introduce myself directly. "
            "Would you be open to a quick founder-to-founder conversation?"
        )
    if step == 2:
        return (
            f"{name}, many operators are strong in the field but underprepared for strategic options. "
            "We help improve leverage before timing gets forced. "
            "Want me to share two practical moves owners are using right now?"
        )
    return (
        f"{name}, if now is not ideal timing, no problem. "
        "If it is useful, we can keep it simple and spend 20 minutes on where things stand today "
        "and what could improve optionality over the next 12-24 months. Worth scheduling?"
    )


@router.get("/samples")
def get_samples() -> dict[str, object]:
    if not SAMPLE_PATH.exists():
        return {
            "samples": [],
            "message": f"Sample file not found at {SAMPLE_PATH}",
        }

    samples: list[dict[str, str]] = []
    with open(SAMPLE_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if len(samples) >= 10:
                break

            first_name = _row_get(row, "first_name", "First Name")
            last_name = _row_get(row, "last_name", "Last Name")
            full_name = _row_get(row, "full_name", "Full Name") or " ".join(
                p for p in [first_name, last_name] if p
            )
            title = _row_get(row, "title", "Title")
            company = _row_get(row, "company", "Company Name", "company_name")
            audience = _row_get(row, "audience") or _infer_audience(title)

            record = {
                "full_name": full_name,
                "title": title,
                "company": company,
                "audience": audience,
                "subject_1": _row_get(row, "subject_1", "subject_step_1"),
                "email_step_1": _row_get(row, "email_step_1", "step_1"),
                "subject_2": _row_get(row, "subject_2", "subject_step_2"),
                "email_step_2": _row_get(row, "email_step_2", "step_2"),
                "subject_3": _row_get(row, "subject_3", "subject_step_3"),
                "email_step_3": _row_get(row, "email_step_3", "step_3"),
            }

            # Prefer canonical pipeline column names (subject_step_N);
            # fall back to deriving from body only if missing.
            for i in (1, 2, 3):
                s_key = f"subject_{i}"
                step_key = f"subject_step_{i}"
                b_key = f"email_step_{i}"
                if not record.get(s_key):
                    record[s_key] = row.get(step_key, "") or _extract_subject(
                        row.get(b_key, "")
                    )

            # Final fallback for contact-only CSVs without generated sequence columns.
            for i in (1, 2, 3):
                s_key = f"subject_{i}"
                b_key = f"email_step_{i}"
                if not record.get(s_key):
                    record[s_key] = _fallback_subject(i, company, audience)
                if not record.get(b_key):
                    record[b_key] = _fallback_body(i, first_name, company, audience)

            samples.append(record)

    return {"samples": samples}
