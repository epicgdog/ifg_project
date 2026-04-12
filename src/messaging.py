from __future__ import annotations

import json

from .models import ClassifiedContact
from .openrouter_client import OpenRouterClient


SYSTEM_PROMPT = (
    "You write concise founder-led outbound emails. "
    "Voice: plainspoken, respectful, blue-collar operator credibility, no hype. "
    "No fluff, no fake claims, no generic mass-email phrasing. "
    "Output strict JSON with keys step_1, step_2, step_3 and string values only."
)


def _audience_instructions(audience: str) -> str:
    if audience == "referral_advocate":
        return (
            "Recipient is a trusted advisor with access to blue-collar owners. "
            "Goal is relationship-first referral conversation, not hard pitch."
        )
    return (
        "Recipient is likely a blue-collar owner/operator. "
        "Goal is founder-to-founder intro and a low-pressure conversation."
    )


def build_sequence_prompt(item: ClassifiedContact) -> str:
    c = item.contact
    first_name = c.first_name or (c.full_name.split(" ")[0] if c.full_name else "there")
    return f"""
Generate a 3-step email sequence.

Audience instructions:
{_audience_instructions(item.audience)}

Contact context:
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

Constraints:
- Each step must be 80-150 words.
- Keep it human, specific, and direct.
- Include exactly one CTA question in each step.
- Avoid spam lines like "just checking in" or "hope you're well".
- Sign as: Kory Mitchell

Output JSON only:
{{"step_1":"...","step_2":"...","step_3":"..."}}
""".strip()


def generate_sequence(
    item: ClassifiedContact, llm: OpenRouterClient, dry_run: bool
) -> dict[str, str]:
    if dry_run:
        name = item.contact.first_name or item.contact.full_name or "there"
        if item.audience == "referral_advocate":
            return {
                "step_1": f"{name}, I run IFG and spend most of my time with blue-collar founders thinking about growth and exit timing. Your work puts you close to owners making big decisions, so I wanted to introduce myself directly. Would you be open to a short call to compare notes on what these owners are asking for most right now?\n\n- Kory Mitchell",
                "step_2": f"{name}, one thing we see often is owners waiting too long to prepare for transition, then losing leverage. We help them tighten operations and narrative before they ever go to market. If useful, I can share a simple pattern we use that advisors pass to clients early. Worth sending over?\n\n- Kory Mitchell",
                "step_3": f"{name}, if referral conversations are easier with context, I can send a one-page overview of the exact founder profile where IFG is most helpful, and where we are not. Would that be useful for you and your team?\n\n- Kory Mitchell",
            }

        return {
            "step_1": f"{name}, I am Kory Mitchell. I built my career in blue-collar businesses and now advise founders through IFG on growth and eventual exits. Your company stood out to me because operator-led businesses in your space are creating real value right now. Open to a short founder-to-founder call to compare what is working in your market?\n\n- Kory Mitchell",
            "step_2": f"{name}, one thing I hear from owners repeatedly is they are strong operationally but have not translated that into a clear exit-ready story. We help tighten that gap while the business keeps growing. If helpful, I can send two practical moves owners are using this quarter. Want me to send them?\n\n- Kory Mitchell",
            "step_3": f"{name}, I know timing has to be right for this kind of conversation. If now is not ideal, no issue. If it is, we can keep it simple and spend 20 minutes on where your business sits today and what could improve leverage over the next 12-24 months. Worth putting on the calendar?\n\n- Kory Mitchell",
        }

    raw = llm.generate(SYSTEM_PROMPT, build_sequence_prompt(item), temperature=0.65)
    data = json.loads(raw)
    for key in ("step_1", "step_2", "step_3"):
        if key not in data or not isinstance(data[key], str):
            raise RuntimeError(f"LLM response missing key: {key}")
    return data
