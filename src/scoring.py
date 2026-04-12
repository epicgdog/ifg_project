from __future__ import annotations

import re

from .models import ClassifiedContact, Contact


OWNER_TITLE_HINTS = {
    "owner",
    "founder",
    "ceo",
    "president",
    "principal",
    "partner",
}

RA_HINTS = {
    "wealth",
    "insurance",
    "broker",
    "fractional cfo",
    "cfo",
    "eos",
    "cepa",
    "banker",
    "advisor",
    "advisory",
    "consultant",
}

BLUE_COLLAR_HINTS = {
    "hvac",
    "roof",
    "landscap",
    "remediation",
    "wastewater",
    "industrial",
    "plumbing",
    "electrical",
    "construction",
    "contractor",
    "services",
}


def _parse_int(value: str) -> int:
    digits = re.sub(r"[^0-9]", "", value or "")
    return int(digits) if digits else 0


def _match_terms(text: str, hints: set[str]) -> list[str]:
    t = text.lower()
    return sorted([h for h in hints if h in t])


def _owner_readiness(
    contact: Contact, audience: str
) -> tuple[str, float, list[str], dict[str, int]]:
    """
    Soft-gating model for owner audience readiness.
    No hard exclusion: returns tier + confidence and evidence.
    """
    if audience != "owner":
        return (
            "n/a",
            0.0,
            ["Not scored for owner readiness (audience is referral_advocate)"],
            {"base": 0},
        )

    details = {"base": 20}
    reasons: list[str] = []
    score = 20

    title_text = contact.title.lower()
    industry_text = " ".join([contact.industry.lower(), contact.notes.lower()])

    title_hits = _match_terms(title_text, OWNER_TITLE_HINTS)
    if title_hits:
        details["owner_title"] = 25
        score += 25
        reasons.append(f"Owner/operator title signal: {', '.join(title_hits[:3])}")

    industry_hits = _match_terms(industry_text, BLUE_COLLAR_HINTS)
    if industry_hits:
        details["blue_collar_vertical"] = 20
        score += 20
        reasons.append(f"Blue-collar vertical signal: {', '.join(industry_hits[:3])}")

    employee_count = _parse_int(contact.employee_count)
    if employee_count >= 20:
        details["employee_count"] = 15
        score += 15
        reasons.append(
            f"Employee count supports larger operator profile ({employee_count})"
        )
    elif employee_count >= 5:
        details["employee_count"] = 8
        score += 8
        reasons.append(f"Employee count present ({employee_count})")

    revenue = _parse_int(contact.annual_revenue)
    if revenue >= 12_000_000:
        details["revenue_proxy"] = 20
        score += 20
        reasons.append("Revenue proxy supports likely $3M+ EBITDA band")
    elif revenue >= 6_000_000:
        details["revenue_proxy"] = 12
        score += 12
        reasons.append("Revenue proxy suggests possible target EBITDA range")
    elif revenue > 0:
        details["revenue_proxy"] = 6
        score += 6
        reasons.append("Revenue present but below ideal proxy threshold")

    data_fields = 0
    for value in [
        contact.title,
        contact.industry,
        contact.website,
        contact.city,
        contact.state,
    ]:
        if value:
            data_fields += 1
    if data_fields >= 4:
        details["data_completeness"] = 10
        score += 10
        reasons.append("Good data completeness for owner assessment")
    elif data_fields >= 2:
        details["data_completeness"] = 5
        score += 5
        reasons.append("Moderate data completeness")

    score = max(0, min(100, score))
    if score >= 75:
        tier = "high"
    elif score >= 55:
        tier = "medium"
    else:
        tier = "low"

    confidence = round(score / 100, 2)
    if not reasons:
        reasons.append("Limited owner-readiness evidence in current data")

    return tier, confidence, reasons, details


def classify(contact: Contact) -> ClassifiedContact:
    title = contact.title.lower()
    industry = contact.industry.lower()
    notes = contact.notes.lower()
    joined = " ".join([title, industry, notes])

    owner_hits = _match_terms(title, OWNER_TITLE_HINTS)
    ra_hits = _match_terms(joined, RA_HINTS)
    blue_collar_hits = _match_terms(joined, BLUE_COLLAR_HINTS)

    is_owner = bool(owner_hits)
    is_ra = bool(ra_hits)

    if is_ra and not is_owner:
        audience = "referral_advocate"
        audience_reason = "Advisor-style title or profile keywords detected"
    else:
        audience = "owner"
        audience_reason = "Operator/founder title pattern detected"

    score = 40
    adjustments: list[dict[str, object]] = []
    matched_signals: list[str] = []

    if is_owner:
        score += 20
        adjustments.append({"rule": "owner_title", "delta": 20, "evidence": owner_hits})
        matched_signals.extend([f"owner:{h}" for h in owner_hits])
    if is_ra:
        score += 15
        adjustments.append(
            {"rule": "advisor_keyword", "delta": 15, "evidence": ra_hits}
        )
        matched_signals.extend([f"ra:{h}" for h in ra_hits])
    if blue_collar_hits:
        score += 20
        adjustments.append(
            {"rule": "blue_collar_vertical", "delta": 20, "evidence": blue_collar_hits}
        )
        matched_signals.extend([f"blue_collar:{h}" for h in blue_collar_hits])
    if contact.website:
        score += 5
        adjustments.append(
            {"rule": "website_present", "delta": 5, "evidence": [contact.website]}
        )
    if contact.city and contact.state:
        score += 5
        adjustments.append(
            {
                "rule": "geo_present",
                "delta": 5,
                "evidence": [f"{contact.city}, {contact.state}"],
            }
        )

    score = max(0, min(100, score))

    tier, confidence, owner_reasons, owner_breakdown = _owner_readiness(
        contact, audience
    )

    reasons = [f"{adj['rule']} (+{adj['delta']})" for adj in adjustments]
    if not reasons:
        reasons = ["Limited profile context"]

    fit_breakdown = {
        "base": 40,
        "adjustments": adjustments,
        "final_score": score,
        "owner_readiness": {
            "tier": tier,
            "confidence": confidence,
            "reasons": owner_reasons,
            "adjustments": owner_breakdown,
        },
    }

    return ClassifiedContact(
        contact=contact,
        audience=audience,
        audience_reason=audience_reason,
        fit_score=score,
        fit_reason="; ".join(reasons),
        fit_breakdown=fit_breakdown,
        matched_signals=matched_signals,
    )
