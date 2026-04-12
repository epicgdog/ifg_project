from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PersonaExample:
    audience: str
    step: int
    tags: list[str]
    text: str


@dataclass
class MasterPersona:
    source_path: str
    identity_summary: str
    tone_rules: list[str] = field(default_factory=list)
    lexicon: list[str] = field(default_factory=list)
    philosophy: list[str] = field(default_factory=list)
    email_rules: list[str] = field(default_factory=list)
    signature_phrases: list[str] = field(default_factory=list)
    examples: list[PersonaExample] = field(default_factory=list)

    def to_prompt_section(self) -> str:
        lines = [
            "MASTER Persona Rules (condensed):",
            f"- Identity: {self.identity_summary}",
            "- Tone:",
        ]
        for rule in self.tone_rules[:6]:
            lines.append(f"  - {rule}")

        if self.lexicon:
            lines.append("- Lexicon to blend naturally:")
            for term in self.lexicon[:14]:
                lines.append(f"  - {term}")

        if self.philosophy:
            lines.append("- Business philosophy anchors:")
            for item in self.philosophy[:5]:
                lines.append(f"  - {item}")

        if self.email_rules:
            lines.append("- Email writing rules:")
            for item in self.email_rules[:6]:
                lines.append(f"  - {item}")

        if self.signature_phrases:
            lines.append("- Signature phrasing style:")
            for phrase in self.signature_phrases[:5]:
                lines.append(f"  - {phrase}")

        return "\n".join(lines)

    def select_examples(
        self,
        audience: str,
        step: int,
        context_text: str,
        k: int = 3,
    ) -> list[str]:
        context = context_text.lower()
        scored: list[tuple[int, str]] = []
        for ex in self.examples:
            score = 0
            if ex.audience == audience:
                score += 6
            elif ex.audience == "any":
                score += 2

            if ex.step == step:
                score += 4

            for tag in ex.tags:
                if tag.lower() in context:
                    score += 1

            scored.append((score, ex.text))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected: list[str] = []
        for _, text in scored:
            if text not in selected:
                selected.append(text)
            if len(selected) >= k:
                break
        return selected


def _extract_section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    tail = text[start:]
    next_heading = tail.find("\n## ")
    if next_heading == -1:
        return tail.strip()
    return tail[:next_heading].strip()


def _extract_bullets(section: str) -> list[str]:
    bullets: list[str] = []
    for raw in section.splitlines():
        line = raw.strip()
        if line.startswith("* "):
            cleaned = line[2:].strip()
            cleaned = cleaned.strip("*")
            if cleaned:
                bullets.append(cleaned)
    return bullets


def _split_terms(text: str) -> list[str]:
    text = text.replace("*", "")
    parts = [p.strip() for p in text.split(",")]
    return [p for p in parts if p]


def _build_default_examples() -> list[PersonaExample]:
    return [
        PersonaExample(
            audience="referral_advocate",
            step=1,
            tags=["advisor", "banker", "broker", "referral"],
            text=(
                "Hey {first_name}, I spend most of my time with blue-collar founders and the advisors they trust. "
                "What I will say is the math gets clearer when we diligencing the people before we obsess over slides. "
                "Would you be open to compare notes on the owner profiles you are seeing this quarter?"
            ),
        ),
        PersonaExample(
            audience="referral_advocate",
            step=2,
            tags=["cash flow", "ebitda", "owner"],
            text=(
                "One hard truth I keep seeing is owners chasing top line while free cash flow gets thin. "
                "That is usually where valuation takes a hit later. If useful, I can share a simple way we frame this in blue-collar terms with founders. "
                "Worth sending over?"
            ),
        ),
        PersonaExample(
            audience="referral_advocate",
            step=3,
            tags=["low pressure", "founder", "referral"],
            text=(
                "No pressure on timing. If now is not ideal, no worries. If it helps, we can grab a meal and talk through what good looks like for the owners you advise before they start any formal process. "
                "Would that be useful?"
            ),
        ),
        PersonaExample(
            audience="owner",
            step=1,
            tags=["owner", "operator", "slog", "burnout"],
            text=(
                "Hey {first_name}, I know the slog of running a blue-collar business when equipment breaks and everybody needs you at once. "
                "I have made my share of unmitigated disasters, so I tend to keep this practical. "
                "Open to a short founder-to-founder conversation on what good looks like from here?"
            ),
        ),
        PersonaExample(
            audience="owner",
            step=2,
            tags=["ebitda", "cash", "valuation"],
            text=(
                "Nobody pays for top line alone. Buyers care about what the business throws off in predictable cash. "
                "If helpful, I can share how we tighten the financial house before owners think about process or multiple. "
                "Want me to send that framework?"
            ),
        ),
        PersonaExample(
            audience="owner",
            step=3,
            tags=["replace yourself", "leadership", "exit"],
            text=(
                "A lot of founders wait too long to replace themselves in key areas, then feel boxed in on timing. "
                "If you want, we can do a low-pressure pass on where leverage can improve over the next 12-24 months. "
                "Worth putting 20 minutes on the calendar?"
            ),
        ),
    ]


def load_master_persona(path: Path | str = "MASTER.md") -> MasterPersona:
    master_path = Path(path)
    if not master_path.exists():
        return MasterPersona(
            source_path=str(master_path),
            identity_summary="Founder-led, plainspoken, pragmatic outreach voice.",
            examples=_build_default_examples(),
        )

    raw_text = master_path.read_text(encoding="utf-8")

    identity_section = _extract_section(raw_text, "1. Core Identity & Vibe")
    tone_section = _extract_section(raw_text, "2. Tone and Voice")
    vocab_section = _extract_section(raw_text, "3. Vocabulary and Lexicon")
    philosophy_section = _extract_section(
        raw_text, '4. Core Business Philosophy (The "Why")'
    )
    rules_section = _extract_section(
        raw_text, '5. Email Writing Rules for the "Kory" Persona'
    )

    tone_rules = _extract_bullets(tone_section)
    philosophy = _extract_bullets(philosophy_section)
    email_rules = _extract_bullets(rules_section)

    lexicon: list[str] = []
    signature_phrases: list[str] = []
    for line in vocab_section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("*"):
            continue
        if "Signature Phrasing" in stripped:
            signature_phrases.extend(_split_terms(stripped.split(":", 1)[-1]))
        elif ":" in stripped:
            lexicon.extend(_split_terms(stripped.split(":", 1)[-1]))

    identity_summary = " ".join(
        [
            line.strip()
            for line in identity_section.splitlines()
            if line.strip() and not line.strip().startswith("**")
        ]
    )
    if not identity_summary:
        identity_summary = "Blue-collar boardroom founder voice with humble authority."

    return MasterPersona(
        source_path=str(master_path),
        identity_summary=identity_summary,
        tone_rules=tone_rules,
        lexicon=lexicon,
        philosophy=philosophy,
        email_rules=email_rules,
        signature_phrases=signature_phrases,
        examples=_build_default_examples(),
    )
