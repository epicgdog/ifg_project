from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VoiceProfile:
    """
    Structured voice profile for LLM-based replication.
    This is the static version for Phase 1 (no RAG yet).
    """

    version: str = "1.0"
    name: str = "Kory Mitchell"

    # Core tone traits
    tone_traits: list[str] = field(
        default_factory=lambda: [
            "plainspoken",
            "respectful",
            "blue-collar operator credibility",
            "no hype",
        ]
    )

    # Sentence patterns (common structures)
    sentence_patterns: list[str] = field(
        default_factory=lambda: [
            "Direct opening with name",
            "Short declarative statements",
            "Specific examples over generalities",
            "Questions as CTAs",
        ]
    )

    # Phrase preferences (words/phrases to use)
    phrase_preferences: list[str] = field(
        default_factory=lambda: [
            "I run",
            "spend most of my time with",
            "blue-collar founders",
            "compare notes",
            "tighten operations",
            "exit-ready story",
            "founder-to-founder",
            "low-pressure conversation",
        ]
    )

    # Taboo phrases (words/phrases to avoid)
    taboo_phrases: list[str] = field(
        default_factory=lambda: [
            "just checking in",
            "hope you're well",
            "circle back",
            "touch base",
            "quick question",
            "following up",
            "best regards",
            "kind regards",
            "sincerely",
        ]
    )

    # CTA style
    cta_style: str = "single direct question, low pressure, specific"

    # Signature style
    signature_style: str = "dash + first and last name"

    # Static exemplars (for few-shot prompting, RAG-ready)
    # These will be retrieved dynamically once RAG is implemented
    style_exemplars: list[dict[str, str]] = field(
        default_factory=lambda: [
            {
                "context": "referral_advocate_step_1",
                "exemplar": "I run IFG and spend most of my time with blue-collar founders thinking about growth and exit timing.",
            },
            {
                "context": "owner_step_1",
                "exemplar": "I am Kory Mitchell. I built my career in blue-collar businesses and now advise founders through IFG on growth and eventual exits.",
            },
            {
                "context": "value_prop",
                "exemplar": "We help them tighten operations and narrative before they ever go to market.",
            },
        ]
    )

    # Constraints for generation
    min_words: int = 80
    max_words: int = 150
    min_cta_questions: int = 1
    max_cta_questions: int = 1

    def to_prompt_section(self) -> str:
        """Convert profile to a system prompt section."""
        lines = [
            f"Voice Profile: {self.name} (v{self.version})",
            "",
            "Tone:",
        ]
        for trait in self.tone_traits:
            lines.append(f"- {trait}")

        lines.extend(
            [
                "",
                "Sentence Patterns:",
            ]
        )
        for pattern in self.sentence_patterns:
            lines.append(f"- {pattern}")

        lines.extend(
            [
                "",
                "Preferred Phrases (use naturally):",
            ]
        )
        for phrase in self.phrase_preferences:
            lines.append(f"- {phrase}")

        lines.extend(
            [
                "",
                "Taboo Phrases (NEVER use):",
            ]
        )
        for phrase in self.taboo_phrases:
            lines.append(f"- {phrase}")

        lines.extend(
            [
                "",
                f"CTA Style: {self.cta_style}",
                f"Signature Style: {self.signature_style}",
                "",
                f"Length: {self.min_words}-{self.max_words} words per email",
            ]
        )

        return "\n".join(lines)

    def get_exemplars_for_context(self, audience: str, step: int) -> list[str]:
        """
        Get relevant style exemplars for a given context.
        This is static now; will use RAG retrieval later.
        """
        context_key = f"{audience}_step_{step}"
        matching = []

        for exemplar in self.style_exemplars:
            # Simple matching: include if context matches or is general
            ex_context = exemplar.get("context", "")
            if context_key in ex_context or ex_context in ["value_prop"]:
                matching.append(exemplar["exemplar"])

        # Return up to 3 exemplars
        return matching[:3]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "version": self.version,
            "name": self.name,
            "tone_traits": self.tone_traits,
            "sentence_patterns": self.sentence_patterns,
            "phrase_preferences": self.phrase_preferences,
            "taboo_phrases": self.taboo_phrases,
            "cta_style": self.cta_style,
            "signature_style": self.signature_style,
            "style_exemplars": self.style_exemplars,
            "min_words": self.min_words,
            "max_words": self.max_words,
            "min_cta_questions": self.min_cta_questions,
            "max_cta_questions": self.max_cta_questions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoiceProfile":
        """Load from dictionary."""
        return cls(
            version=data.get("version", "1.0"),
            name=data.get("name", "Kory Mitchell"),
            tone_traits=data.get("tone_traits", []),
            sentence_patterns=data.get("sentence_patterns", []),
            phrase_preferences=data.get("phrase_preferences", []),
            taboo_phrases=data.get("taboo_phrases", []),
            cta_style=data.get("cta_style", ""),
            signature_style=data.get("signature_style", ""),
            style_exemplars=data.get("style_exemplars", []),
            min_words=data.get("min_words", 80),
            max_words=data.get("max_words", 150),
            min_cta_questions=data.get("min_cta_questions", 1),
            max_cta_questions=data.get("max_cta_questions", 1),
        )

    @classmethod
    def load(cls, path: Path | str) -> "VoiceProfile":
        """Load profile from JSON file."""
        path = Path(path)
        if not path.exists():
            # Return default profile
            return cls()

        with open(path, "r") as f:
            data = json.load(f)

        return cls.from_dict(data)

    def save(self, path: Path | str) -> None:
        """Save profile to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# Global profile instance (lazy-loaded)
_profile: VoiceProfile | None = None


def get_voice_profile(profile_path: Path | str | None = None) -> VoiceProfile:
    """Get the voice profile (loads from file or returns default)."""
    global _profile

    if _profile is None:
        if profile_path:
            _profile = VoiceProfile.load(profile_path)
        else:
            # Try to load from default location
            default_path = Path("data/voice_profile.json")
            if default_path.exists():
                _profile = VoiceProfile.load(default_path)
            else:
                _profile = VoiceProfile()
                # Save default for user to edit
                _profile.save(default_path)

    return _profile


def reset_voice_profile() -> None:
    """Reset the cached profile (for testing/hot reload)."""
    global _profile
    _profile = None
