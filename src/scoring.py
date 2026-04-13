from __future__ import annotations

import re

from .models import ClassifiedContact, Contact


def calculate_audience_confidence(
    contact: Contact,
    owner_hits: list[str],
    ra_hits: list[str]
) -> float:
    """Calculate confidence score 0.0-1.0 for audience classification.

    Strong owner signals (CEO/Founder/Owner title): 0.8-1.0
    Strong RA signals (advisor/CFO/wealth/CEPA/EOS): 0.8-1.0
    Mixed/ambiguous: 0.4-0.7
    No clear signals: 0.0-0.3

    Args:
        contact: The contact being classified
        owner_hits: List of owner-related keywords found in contact data
        ra_hits: List of referral advocate keywords found in contact data

    Returns:
        Float confidence score between 0.0 and 1.0
    """
    title = contact.title.lower()

    # Strong owner indicators
    strong_owner = {"ceo", "founder", "owner", "co-founder", "cofounder", "managing partner"}
    is_strong_owner = any(s in title for s in strong_owner)

    # Strong RA indicators
    strong_ra = {"cfo", "fractional cfo", "cepa", "eos", "wealth advisor"}
    is_strong_ra = any(s in title for s in strong_ra) or any(
        s in " ".join(ra_hits) for s in strong_ra
    )

    has_owner = bool(owner_hits)
    has_ra = bool(ra_hits)

    if is_strong_owner and not has_ra:
        return round(0.9, 2)
    elif is_strong_ra and not has_owner:
        return round(0.9, 2)
    elif has_owner and not has_ra:
        return round(0.8, 2)
    elif has_ra and not has_owner:
        return round(0.8, 2)
    elif has_owner and has_ra:
        return round(0.55, 2)
    else:
        return round(0.25, 2)


def estimate_maturity_score(contact: Contact) -> int:
    """Estimate company maturity 0-100 from available data.

    Returns contact.company_maturity_score if already set (> 0),
    otherwise estimates from employee_count, website, etc.

    Scoring:
    - Base: 30
    - Has real website (not empty): +15
    - Employee count 10-49: +10, 50+: +20
    - Website mentions years/founded: +10-25
    - Professional email domain: +10

    Args:
        contact: The contact with company information

    Returns:
        Integer maturity score between 0 and 100
    """
    # Use existing maturity score from research if available
    if contact.company_maturity_score > 0:
        return contact.company_maturity_score

    score = 30  # Base score

    # Website presence
    website = (contact.website or "").strip()
    if website and website.lower() not in ("", "n/a", "null", "-", "none"):
        score += 15

    # Employee count tiers
    employee_count = _parse_int(contact.employee_count)
    if employee_count >= 50:
        score += 20
    elif employee_count >= 10:
        score += 10
    elif employee_count >= 1:
        score += 5

    # Website maturity keywords
    maturity_keywords = ["founded", "since", "established", "years", "experience"]
    website_lower = contact.website.lower() if contact.website else ""
    notes_lower = contact.notes.lower() if contact.notes else ""
    for keyword in maturity_keywords:
        if keyword in website_lower or keyword in notes_lower:
            score += 10
            break

    # Professional email domain
    email = (contact.email or "").lower()
    personal_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com"}
    if "@" in email:
        domain = email.split("@")[1]
        if domain and domain not in personal_domains:
            score += 10

    return min(100, score)


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

    # Factor in decision maker info from agentic research if available
    if contact.decision_maker_name and contact.decision_maker_title:
        details["decision_maker_identified"] = 10
        score += 10
        reasons.append(f"Decision maker identified: {contact.decision_maker_name}")

    # Factor in company maturity score
    maturity = estimate_maturity_score(contact)
    if maturity >= 70:
        details["maturity_high"] = 8
        score += 8
        reasons.append(f"High company maturity score ({maturity})")
    elif maturity >= 50:
        details["maturity_medium"] = 5
        score += 5
        reasons.append(f"Medium company maturity score ({maturity})")

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

    if is_ra:
        audience = "referral_advocate"
        audience_reason = (
            "Advisor-style title or profile keywords detected"
            if not is_owner
            else "Advisor-style keywords present alongside owner title; routing to referral_advocate"
        )
    elif is_owner:
        audience = "owner"
        audience_reason = "Operator/founder title pattern detected"
    else:
        audience = "owner"
        audience_reason = "No clear advisor signals; defaulting to owner"

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

    # Calculate new agentic research fields
    audience_confidence = calculate_audience_confidence(contact, owner_hits, ra_hits)
    maturity_score = estimate_maturity_score(contact)
    maturity_assessment = "from_research" if contact.company_maturity_score > 0 else "estimated"

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
        "audience_confidence": audience_confidence,
        "maturity_score": maturity_score,
        "maturity_assessment": maturity_assessment,
    }

    return ClassifiedContact(
        contact=contact,
        audience=audience,
        audience_reason=audience_reason,
        fit_score=score,
        fit_reason="; ".join(reasons),
        audience_confidence=audience_confidence,
        fit_breakdown=fit_breakdown,
        matched_signals=matched_signals,
        maturity_score=maturity_score,
    )
