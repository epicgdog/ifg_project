"""EBITDA-based qualification filter.

Applied AFTER enrichment but BEFORE classification/qualification. Uses
``annual_revenue * 0.15`` as a rough EBITDA proxy when an explicit ``ebitda``
value isn't attached to the contact. Contacts missing revenue data are kept
(we don't drop on missing data).
"""
from __future__ import annotations

import re
from typing import Any, Iterable


def _parse_money(value: Any) -> int | None:
    """Parse a currency-ish string/number to an int. Returns None if unparseable."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if value else None
    s = str(value).strip()
    if not s:
        return None
    digits = re.sub(r"[^0-9]", "", s)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def estimate_ebitda(contact: Any) -> int | None:
    """Return an EBITDA estimate for the contact, or None if unknown."""
    explicit = getattr(contact, "ebitda", None)
    parsed = _parse_money(explicit)
    if parsed is not None:
        return parsed

    revenue = _parse_money(getattr(contact, "annual_revenue", ""))
    if revenue is None:
        return None
    return int(revenue * 0.15)


def filter_by_min_ebitda(contacts: Iterable[Any], min_ebitda: int) -> list[Any]:
    """Filter contacts by a minimum estimated EBITDA threshold.

    Missing data is preserved (contacts without revenue info are kept).
    """
    if not min_ebitda or min_ebitda <= 0:
        return list(contacts)

    kept: list[Any] = []
    for contact in contacts:
        estimated = estimate_ebitda(contact)
        if estimated is None:
            # Keep contacts with unknown revenue
            kept.append(contact)
            continue
        if estimated >= min_ebitda:
            kept.append(contact)
    return kept
