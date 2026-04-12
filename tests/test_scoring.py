from __future__ import annotations

from src.models import Contact
from src.scoring import classify


def _contact(**overrides) -> Contact:
    defaults = dict(
        row_id="t:1",
        source_file="test.csv",
        first_name="Test",
        last_name="User",
        full_name="Test User",
        title="",
        company="",
        email="test@example.com",
        industry="",
        website="",
        linkedin="",
        city="",
        state="",
        notes="",
        employee_count="",
        annual_revenue="",
        apollo_person_id="",
        apollo_org_id="",
    )
    defaults.update(overrides)
    return Contact(**defaults)


def test_classify_detects_owner_title():
    """Owner/founder/president titles classify as 'owner'."""
    c = _contact(title="Owner", company="Morrison Roofing")
    result = classify(c)
    assert result.audience == "owner"
    assert any("owner" in s for s in result.matched_signals)


def test_classify_detects_referral_advocate():
    """Advisor-style titles (fractional CFO, wealth, broker) classify as RA."""
    c = _contact(title="Fractional CFO", company="Price Advisory")
    result = classify(c)
    assert result.audience == "referral_advocate"
    assert any(s.startswith("ra:") for s in result.matched_signals)


def test_blue_collar_hint_bumps_fit_score():
    """Matching a blue-collar vertical keyword adds to fit_score vs baseline."""
    plain = _contact(title="Owner")
    blue = _contact(title="Owner", industry="Roofing", notes="commercial roof crew")

    plain_result = classify(plain)
    blue_result = classify(blue)

    assert blue_result.fit_score > plain_result.fit_score
    assert any("blue_collar" in s for s in blue_result.matched_signals)


def test_generic_title_falls_back_to_owner():
    """Titles that match neither owner nor RA hints fall back to owner."""
    c = _contact(title="Operations Manager", company="Something Inc")
    result = classify(c)
    # No RA keyword hit and no owner keyword either -> default owner bucket.
    assert result.audience == "owner"


def test_fit_score_is_bounded_zero_to_hundred():
    """Even with every signal stacked, fit_score stays within [0, 100]."""
    c = _contact(
        title="Owner Founder CEO President Partner",  # multiple owner hints
        industry="hvac roofing plumbing construction industrial",
        notes="wealth insurance broker advisor eos",  # stacks RA hits too
        website="https://example.com",
        city="Dallas",
        state="TX",
    )
    result = classify(c)
    assert 0 <= result.fit_score <= 100
