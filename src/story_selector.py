"""Dynamic story injection for personalized email sequences.

Scores Kory Mitchell's founder stories against a contact's context (industry,
title, pain signals) and returns the best-matching story to weave into the
generation prompt. No vector DB required — BM25-style keyword overlap is
sufficient for a bank of ~20 stories.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Story:
    id: str
    title: str
    narrative: str
    trigger_keywords: list[str]
    pain_signals: list[str]
    best_for_step: list[int]
    audiences: list[str]


class StorySelector:
    """Loads the story bank once and scores stories against contact context."""

    # Minimum relevance score to include a story (avoids injecting irrelevant ones).
    MIN_SCORE = 3

    def __init__(self, story_bank_path: str | Path = "data/story_bank.json"):
        self.stories = self._load(Path(story_bank_path))

    def _load(self, path: Path) -> list[Story]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [Story(**s) for s in data.get("stories", [])]
        except (json.JSONDecodeError, TypeError):
            return []

    def select(
        self,
        context_text: str,
        audience: str,
        step: int = 1,
        k: int = 1,
    ) -> list[Story]:
        """Return up to *k* stories most relevant to the given contact context.

        Scoring weights:
        - Audience match:      +4
        - Step match:          +2
        - Trigger keyword hit: +3 each (industry / vertical signals)
        - Pain signal hit:     +1 each (softer behavioural signals)
        """
        ctx = context_text.lower()
        scored: list[tuple[int, Story]] = []

        for story in self.stories:
            score = 0

            if audience in story.audiences or "any" in story.audiences:
                score += 4

            if step in story.best_for_step:
                score += 2

            for kw in story.trigger_keywords:
                if kw.lower() in ctx:
                    score += 3

            for signal in story.pain_signals:
                if signal.lower() in ctx:
                    score += 1

            if score >= self.MIN_SCORE:
                scored.append((score, story))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [story for _, story in scored[:k]]

    def format_for_prompt(self, stories: list[Story]) -> str:
        """Format selected stories as a prompt section."""
        if not stories:
            return ""
        lines = [
            "Founder Story to Reference (weave naturally into the email — do not copy verbatim):",
        ]
        for story in stories:
            lines.append(f'"{story.narrative}"')
            lines.append(
                "Use this to establish shared experience or credibility, not to pitch. "
                "Compress, adapt, or allude to it — adapt the detail level to the contact."
            )
        return "\n".join(lines)


# Module-level singleton — loaded once per process, shared across threads.
_selector: StorySelector | None = None


def get_story_selector(story_bank_path: str | Path = "data/story_bank.json") -> StorySelector:
    global _selector
    if _selector is None:
        _selector = StorySelector(story_bank_path)
    return _selector
