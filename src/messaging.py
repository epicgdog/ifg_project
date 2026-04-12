from __future__ import annotations

import json
from typing import Any

from .models import ClassifiedContact, GeneratedSequence
from .openrouter_client import OpenRouterClient
from .validators import JSONValidator, SequenceValidator
from .voice_profile import get_voice_profile


def _audience_instructions(audience: str) -> str:
    """Get audience-specific instructions."""
    if audience == "referral_advocate":
        return (
            "Recipient is a trusted advisor with access to blue-collar owners. "
            "Goal is relationship-first referral conversation, not hard pitch."
        )
    return (
        "Recipient is likely a blue-collar owner/operator. "
        "Goal is founder-to-founder intro and a low-pressure conversation."
    )


def build_sequence_prompt(
    item: ClassifiedContact, voice_profile: Any | None = None
) -> str:
    """
    Build the generation prompt with voice profile and context.

    This is RAG-ready: the voice_profile.get_exemplars_for_context() call
    will be replaced with actual retrieval once RAG is implemented.
    """
    if voice_profile is None:
        voice_profile = get_voice_profile()

    c = item.contact
    first_name = c.first_name or (c.full_name.split(" ")[0] if c.full_name else "there")

    # Get style exemplars for this context (static now, RAG later)
    exemplars = voice_profile.get_exemplars_for_context(item.audience, 1)
    exemplar_text = "\n".join([f"- {ex}" for ex in exemplars]) if exemplars else ""

    # Build data provenance section
    provenance = []
    if c.enrichment_sources:
        fields_by_source = {}
        for field, source in c.enrichment_sources.items():
            fields_by_source.setdefault(source, []).append(field)
        for source, fields in fields_by_source.items():
            provenance.append(f"- {source}: {', '.join(fields)}")

    provenance_text = (
        "\n".join(provenance) if provenance else "- csv: all fields from import"
    )

    prompt = f"""Generate a 3-step email sequence in the specified voice.

Voice Profile:
{voice_profile.to_prompt_section()}

Style Examples (adapt naturally, do not copy verbatim):
{exemplar_text}

Audience Instructions:
{_audience_instructions(item.audience)}

Contact Context:
- First name: {first_name}
- Full name: {c.full_name}
- Title: {c.title}
- Company: {c.company}
- Industry: {c.industry}
- City/State: {c.city}, {c.state}
- Website: {c.website}
- Notes: {c.notes}
- Audience reason: {item.audience_reason}
- Fit reason: {item.fit_reason}

Data Sources:
{provenance_text}

Output Requirements:
- Output ONLY valid JSON with keys step_1, step_2, step_3
- Each step must be 80-150 words
- Each step must have exactly one CTA question
- Keep it human, specific, and direct
- Avoid spam lines like "just checking in" or "hope you're well"
- Sign as: {voice_profile.name}

JSON Output:
{{"step_1":"...","step_2":"...","step_3":"..."}}
""".strip()

    return prompt


def build_system_prompt(voice_profile: Any | None = None) -> str:
    """Build the system prompt with voice constraints."""
    if voice_profile is None:
        voice_profile = get_voice_profile()

    return (
        f"You write concise founder-led outbound emails in the style of {voice_profile.name}. "
        "Voice: plainspoken, respectful, blue-collar operator credibility, no hype. "
        "No fluff, no fake claims, no generic mass-email phrasing. "
        "Output strict JSON with keys step_1, step_2, step_3 and string values only."
    )


def _generate_dry_run_sequence(item: ClassifiedContact) -> dict[str, str]:
    """Generate deterministic placeholder sequences for dry-run mode."""
    name = item.contact.first_name or item.contact.full_name or "there"
    voice = get_voice_profile()

    if item.audience == "referral_advocate":
        return {
            "step_1": f"{name}, I run IFG and spend most of my time with blue-collar founders thinking about growth and exit timing. Your work puts you close to owners making big decisions, so I wanted to introduce myself directly. Would you be open to a short call to compare notes on what these owners are asking for most right now?\n\n- {voice.name}",
            "step_2": f"{name}, one thing we see often is owners waiting too long to prepare for transition, then losing leverage. We help them tighten operations and narrative before they ever go to market. If useful, I can share a simple pattern we use that advisors pass to clients early. Worth sending over?\n\n- {voice.name}",
            "step_3": f"{name}, if referral conversations are easier with context, I can send a one-page overview of the exact founder profile where IFG is most helpful, where we are not, and the types of owners who usually engage after one intro call. Would that be useful for you and your team this quarter?\n\n- {voice.name}",
        }

    return {
        "step_1": f"{name}, I am {voice.name}. I built my career in blue-collar businesses and now advise founders through IFG on growth and eventual exits. Your company stood out to me because operator-led businesses in your space are creating real value right now. Open to a short founder-to-founder call to compare what is working in your market?\n\n- {voice.name}",
        "step_2": f"{name}, one thing I hear from owners repeatedly is they are strong operationally but have not translated that into a clear exit-ready story. We help tighten that gap while the business keeps growing. If helpful, I can send two practical moves owners are using this quarter. Want me to send them?\n\n- {voice.name}",
        "step_3": f"{name}, I know timing has to be right for this kind of conversation. If now is not ideal, no issue. If it is, we can keep it simple and spend 20 minutes on where your business sits today and what could improve leverage over the next 12-24 months. Worth putting on the calendar?\n\n- {voice.name}",
    }


def generate_sequence(
    item: ClassifiedContact, llm: OpenRouterClient, dry_run: bool = False
) -> GeneratedSequence:
    """
    Generate and validate a 3-step email sequence.

    Args:
        item: Classified contact with context
        llm: LLM client for generation
        dry_run: If True, return deterministic placeholders without API call

    Returns:
        GeneratedSequence with validation metadata
    """
    validator = SequenceValidator()

    if dry_run:
        sequence_data = _generate_dry_run_sequence(item)
        return validator.validate_sequence(sequence_data, strict=False)

    # Build prompts with voice profile
    voice_profile = get_voice_profile()
    system_prompt = build_system_prompt(voice_profile)
    user_prompt = build_sequence_prompt(item, voice_profile)

    # Generate with LLM
    raw = llm.generate(system_prompt, user_prompt, temperature=0.65)

    # Parse JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        # Attempt to extract JSON from markdown code blocks
        import re

        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                raise RuntimeError(f"LLM returned invalid JSON: {e}")
        else:
            raise RuntimeError(f"LLM returned invalid JSON: {e}")

    # Validate structure
    structure_result = JSONValidator.validate_structure(data)
    if not structure_result.passed:
        raise RuntimeError(f"LLM response structure invalid: {structure_result.errors}")

    # Validate content quality
    validated_sequence = validator.validate_sequence(data)

    return validated_sequence
