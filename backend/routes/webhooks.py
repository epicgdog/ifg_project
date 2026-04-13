"""Webhook intake for Instantly.ai delivery events.

Instantly fires a POST to this endpoint on: open, click, reply, bounce,
unsubscribe, opt_out.  Events are appended as NDJSON to out/outreach_events.ndjson
so they can be read by any downstream tool without a database.

To wire up in Instantly:
  Campaigns → Settings → Webhooks → Add endpoint
  URL: https://your-backend.com/api/webhooks/instantly
  Events: opened, replied, clicked, bounced

Security: set INSTANTLY_WEBHOOK_SECRET in your .env and Instantly will sign
each request with X-Instantly-Signature (HMAC-SHA256 of the raw body).
Verification is enabled automatically when the env var is present.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

EVENT_LOG = Path("out/outreach_events.ndjson")
_KNOWN_EVENTS = {"opened", "clicked", "replied", "bounced", "unsubscribed", "opt_out"}


@dataclass
class OutreachEvent:
    timestamp: str
    event_type: str
    email: str
    step: int | None
    campaign_id: str
    lead_id: str
    subject: str
    raw: dict[str, Any] = field(default_factory=dict)


def _verify_signature(secret: str, body: bytes, signature: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _append_event(event: OutreachEvent) -> None:
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event)) + "\n")


@router.post("/instantly")
async def instantly_webhook(request: Request) -> Response:
    body = await request.body()

    secret = os.getenv("INSTANTLY_WEBHOOK_SECRET", "")
    if secret:
        sig = request.headers.get("X-Instantly-Signature", "")
        if not sig or not _verify_signature(secret, body, sig):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = str(payload.get("event_type") or payload.get("type") or "unknown").lower()

    event = OutreachEvent(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        event_type=event_type,
        email=str(payload.get("email_address") or payload.get("email") or ""),
        step=_safe_int(payload.get("step") or payload.get("sequence_step")),
        campaign_id=str(payload.get("campaign_id") or ""),
        lead_id=str(payload.get("lead_id") or ""),
        subject=str(payload.get("subject") or ""),
        raw=payload,
    )

    _append_event(event)
    return Response(content='{"ok":true}', media_type="application/json")


@router.get("/instantly/events")
def list_events(limit: int = 100) -> list[dict[str, Any]]:
    """Return the most recent *limit* outreach events (newest first)."""
    if not EVENT_LOG.exists():
        return []
    lines = EVENT_LOG.read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(events) >= limit:
            break
    return events


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
