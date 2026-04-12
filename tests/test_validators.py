from __future__ import annotations

from src.validators import JSONValidator, SequenceValidator
from src.voice_profile import reset_voice_profile


def setup_function(_):
    # Ensure each test starts with a fresh cached voice profile to avoid
    # cross-test state from previous test modules that may have mutated it.
    reset_voice_profile()


def _build_good_step(name: str = "Kory Mitchell", extra_filler: int = 0) -> str:
    """Produce a ~90-word email body with proper signature and one CTA."""
    base = (
        "Hey there, I run IFG and spend most of my time with blue-collar founders "
        "thinking through growth and exit planning in a practical, founder-first way. "
        "Your business stood out because operator-led companies in your space are "
        "creating real durable value right now across multiple regions. I keep these "
        "notes short and specific to respect your time and focus. "
        "Would you be open to a short founder-to-founder call to compare what is "
        "working in your market"
    )
    filler = " Extra context here." * extra_filler
    return f"{base}{filler}?\n\n- {name}"


def test_taboo_phrase_is_flagged_as_error():
    """Using a taboo phrase like 'just checking in' produces a validation error."""
    sv = SequenceValidator()
    bad = (
        "Hey there, just checking in on the conversation we had. I run IFG and spend "
        "most of my time with blue-collar founders thinking through growth and exit. "
        "Your business stood out because operator-led companies in your space are "
        "creating real durable value right now across multiple regions in ways that "
        "buyers respect. Would you be open to a short call?\n\n- Kory Mitchell"
    )
    result = sv.validate_step(bad, "step_1")
    assert not result.passed
    assert any("taboo" in e.lower() for e in result.errors)


def test_signature_required():
    """A step missing the signature line is flagged."""
    sv = SequenceValidator()
    body = (
        "Hey there, I run IFG and spend most of my time with blue-collar founders "
        "thinking through growth and exit planning in a practical, founder-first way. "
        "Your business stood out because operator-led companies in your space are "
        "creating real durable value right now across multiple regions. I keep these "
        "notes short and specific to respect your time. Would you be open to a short "
        "call to compare what is working in your market?"
    )
    result = sv.validate_step(body, "step_1")
    assert not result.passed
    assert any("signature" in e.lower() for e in result.errors)


def test_too_short_step_errors():
    """A body well under min_words is flagged as too short."""
    sv = SequenceValidator()
    short = "Hey. Want to chat?\n\n- Kory Mitchell"
    result = sv.validate_step(short, "step_1")
    assert not result.passed
    assert any("too short" in e.lower() for e in result.errors)


def test_too_long_step_errors():
    """A body well over max_words is flagged as too long."""
    sv = SequenceValidator()
    # 200 repeated words well over the 150-word ceiling.
    long_body = ("word " * 200) + "Would you have time for a call?\n\n- Kory Mitchell"
    result = sv.validate_step(long_body, "step_1")
    assert not result.passed
    assert any("too long" in e.lower() for e in result.errors)


def test_missing_cta_question_errors():
    """A step without any '?' fails the CTA check."""
    sv = SequenceValidator()
    no_cta = (
        "Hey there, I run IFG and spend most of my time with blue-collar founders. "
        "Your business stood out because operator-led companies in your space are "
        "creating real durable value right now across multiple regions. I keep these "
        "notes short and specific to respect your time and focus on what matters. "
        "Happy to compare notes whenever works best for your calendar later.\n\n"
        "- Kory Mitchell"
    )
    result = sv.validate_step(no_cta, "step_1")
    assert not result.passed
    assert any("cta" in e.lower() for e in result.errors)


def test_multiple_questions_is_warning_not_error():
    """More than one '?' is a warning (not an error)."""
    sv = SequenceValidator()
    two_q = (
        "Hey there, I run IFG and spend most of my time with blue-collar founders "
        "thinking through growth and exit planning in a practical, founder-first way "
        "that tends to resonate with people who have built real operations with real "
        "teams over many years of disciplined effort. Your business stood out because "
        "operator-led companies in your space are creating real durable value right "
        "now across multiple regions, and that momentum looks worth understanding. "
        "Would you be open to a short call? And what would good look like for you "
        "this quarter?\n\n- Kory Mitchell"
    )
    result = sv.validate_step(two_q, "step_1")
    # No "missing CTA" error; extra question is a warning only.
    assert not any(
        "missing cta" in e.lower() for e in result.errors
    ), f"unexpected errors: {result.errors}"
    assert any("multiple" in w.lower() for w in result.warnings)


def test_json_structure_requires_all_six_keys():
    """JSONValidator.validate_structure rejects payloads missing required keys."""
    missing = {"step_1": "a", "step_2": "b", "step_3": "c"}
    result = JSONValidator.validate_structure(missing)
    assert not result.passed
    errors_joined = " ".join(result.errors).lower()
    assert "subject_1" in errors_joined
    assert "subject_2" in errors_joined
    assert "subject_3" in errors_joined

    complete = {
        "step_1": "a",
        "step_2": "b",
        "step_3": "c",
        "subject_1": "x",
        "subject_2": "y",
        "subject_3": "z",
    }
    assert JSONValidator.validate_structure(complete).passed


def test_subject_line_banned_phrase_flagged():
    """SequenceValidator.validate_subject flags 'Quick question' and 'Re:'."""
    sv = SequenceValidator()
    r1 = sv.validate_subject("Quick question about roofing", "subject_1")
    assert not r1.passed
    assert any("banned" in e.lower() for e in r1.errors)

    r2 = sv.validate_subject("Re: our earlier thread", "subject_1")
    assert not r2.passed
    assert any("re:" in e.lower() for e in r2.errors)

    r3 = sv.validate_subject("Comparing notes on owner profiles", "subject_1")
    assert r3.passed, r3.errors
