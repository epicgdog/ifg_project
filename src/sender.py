"""Direct send integration for Instantly.ai.

Pushes generated leads from a campaign CSV into an Instantly campaign via the
Instantly API. See https://developer.instantly.ai for the reference.

Environment:
    INSTANTLY_API_KEY  - Instantly API key
    INSTANTLY_BASE_URL - override if needed (default https://api.instantly.ai)
"""

from __future__ import annotations

import csv
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests


logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.instantly.ai"
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass
class InstantlyPushReport:
    attempted: int = 0
    pushed: int = 0
    skipped_no_email: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempted": self.attempted,
            "pushed": self.pushed,
            "skipped_no_email": self.skipped_no_email,
            "failed": self.failed,
            "error_count": len(self.errors),
        }


def _row_to_lead(row: dict[str, str]) -> dict[str, Any] | None:
    email = (row.get("email") or row.get("Email") or "").strip()
    if not email or "@" not in email:
        return None
    return {
        "email": email,
        "first_name": row.get("first_name") or row.get("First Name") or "",
        "last_name": row.get("last_name") or row.get("Last Name") or "",
        "company_name": row.get("company") or row.get("Company") or "",
        "personalization": row.get("email_step_1") or row.get("Step 1") or "",
        "custom_variables": {
            "subject_1": row.get("subject_1") or row.get("Subject 1") or "",
            "step_1": row.get("email_step_1") or row.get("Step 1") or "",
            "subject_2": row.get("subject_2") or row.get("Subject 2") or "",
            "step_2": row.get("email_step_2") or row.get("Step 2") or "",
            "subject_3": row.get("subject_3") or row.get("Subject 3") or "",
            "step_3": row.get("email_step_3") or row.get("Step 3") or "",
            "qualification_tier": row.get("qualification_tier") or "",
            "audience": row.get("audience") or "",
        },
    }


def _post_with_retry(
    url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 30
) -> requests.Response:
    delays = (1.0, 2.0, 4.0)
    last_response: requests.Response | None = None
    for attempt in range(1 + len(delays)):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < len(delays):
                time.sleep(delays[attempt])
                continue
            raise
        if resp.status_code in _RETRYABLE_STATUS and attempt < len(delays):
            retry_after = resp.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else delays[attempt]
            time.sleep(delay)
            last_response = resp
            continue
        return resp
    assert last_response is not None
    return last_response


def push_to_instantly(
    csv_path: str | Path,
    campaign_id: str,
    api_key: str | None = None,
    base_url: str | None = None,
    only_qualified: bool = True,
    batch_size: int = 50,
    dry_run: bool = False,
) -> InstantlyPushReport:
    """Push leads from a campaign CSV to an Instantly campaign.

    Args:
        csv_path: path to campaign_ready.csv or instantly_campaign.csv
        campaign_id: Instantly campaign UUID
        api_key: Instantly API key (falls back to INSTANTLY_API_KEY env)
        base_url: API base URL override
        only_qualified: if True, only push rows where qualified == "yes"
        batch_size: number of leads per POST call
        dry_run: if True, build payloads but do not call the API

    Returns:
        InstantlyPushReport summarizing attempts, pushes, and failures.
    """
    report = InstantlyPushReport()

    api_key = api_key or os.getenv("INSTANTLY_API_KEY", "")
    base_url = (base_url or os.getenv("INSTANTLY_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/")

    if not dry_run and not api_key:
        report.errors.append("INSTANTLY_API_KEY not set")
        return report
    if not campaign_id:
        report.errors.append("campaign_id is required")
        return report

    path = Path(csv_path)
    if not path.exists():
        report.errors.append(f"CSV not found: {csv_path}")
        return report

    leads: list[dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            report.attempted += 1
            if only_qualified and (row.get("qualified") or "").lower() not in ("yes", "true", "1"):
                continue
            lead = _row_to_lead(row)
            if lead is None:
                report.skipped_no_email += 1
                continue
            leads.append(lead)

    if dry_run:
        report.pushed = len(leads)
        return report

    url = f"{base_url}/api/v2/campaigns/{campaign_id}/leads"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for i in range(0, len(leads), batch_size):
        batch = leads[i : i + batch_size]
        payload = {"leads": batch, "skip_if_in_workspace": True, "skip_if_in_campaign": True}
        try:
            resp = _post_with_retry(url, payload, headers)
        except Exception as e:
            report.failed += len(batch)
            report.errors.append(f"batch {i}-{i + len(batch)}: {e}")
            continue

        if resp.status_code >= 400:
            report.failed += len(batch)
            report.errors.append(
                f"batch {i}-{i + len(batch)}: HTTP {resp.status_code} {resp.text[:200]}"
            )
            continue

        report.pushed += len(batch)
        logger.info("Pushed %d leads to Instantly campaign %s", len(batch), campaign_id)

    return report
