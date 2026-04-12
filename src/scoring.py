from __future__ import annotations

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


def _contains_any(text: str, hints: set[str]) -> bool:
    t = text.lower()
    return any(h in t for h in hints)


def classify(contact: Contact) -> ClassifiedContact:
    title = contact.title.lower()
    industry = contact.industry.lower()
    notes = contact.notes.lower()
    joined = " ".join([title, industry, notes])

    is_owner = _contains_any(title, OWNER_TITLE_HINTS)
    is_ra = _contains_any(joined, RA_HINTS)
    blue_collar = _contains_any(joined, BLUE_COLLAR_HINTS)

    if is_ra and not is_owner:
        audience = "referral_advocate"
        audience_reason = "Advisor-style title or profile keywords detected"
    else:
        audience = "owner"
        audience_reason = "Operator/founder title pattern detected"

    score = 40
    reasons: list[str] = []

    if is_owner:
        score += 20
        reasons.append("Leadership title")
    if is_ra:
        score += 15
        reasons.append("Advisor keyword")
    if blue_collar:
        score += 20
        reasons.append("Blue-collar vertical hint")
    if contact.website:
        score += 5
        reasons.append("Company website present")

    if contact.city and contact.state:
        score += 5
        reasons.append("Geo data present")

    score = max(0, min(100, score))

    if not reasons:
        reasons = ["Limited profile context"]

    return ClassifiedContact(
        contact=contact,
        audience=audience,
        audience_reason=audience_reason,
        fit_score=score,
        fit_reason="; ".join(reasons),
    )
