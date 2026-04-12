from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .models import GeneratedSequence
from .voice_profile import get_voice_profile


@dataclass
class ValidationResult:
    """Result of validation checks."""

    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


class SequenceValidator:
    """Validates generated email sequences for quality and compliance."""

    def __init__(self):
        self.profile = get_voice_profile()

    def _count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())

    def _count_questions(self, text: str) -> int:
        """Count question marks in text."""
        return text.count("?")

    def _contains_any(self, text: str, phrases: list[str]) -> list[str]:
        """Check if text contains any of the given phrases."""
        text_lower = text.lower()
        found = []
        for phrase in phrases:
            if phrase.lower() in text_lower:
                found.append(phrase)
        return found

    def _check_signature(self, text: str) -> bool:
        """Check if proper signature is present."""
        # Expect "- Kory Mitchell" or similar pattern
        lines = text.strip().split("\n")
        if not lines:
            return False

        # Check last few lines for signature pattern
        for line in lines[-3:]:
            line = line.strip()
            if line.startswith("- ") and self.profile.name in line:
                return True
            if line.startswith("— ") and self.profile.name in line:
                return True
        return False

    def validate_step(
        self, step: str, step_name: str, strict: bool = True
    ) -> ValidationResult:
        """Validate a single email step."""
        errors = []
        warnings = []

        word_count = self._count_words(step)

        # Length check
        min_words = (
            self.profile.min_words if strict else max(40, self.profile.min_words - 30)
        )
        if word_count < min_words:
            errors.append(
                f"{step_name}: Too short ({word_count} words, min {min_words})"
            )
        elif word_count > self.profile.max_words:
            errors.append(
                f"{step_name}: Too long ({word_count} words, max {self.profile.max_words})"
            )
        elif word_count < self.profile.min_words + 10:
            warnings.append(f"{step_name}: Approaching minimum length")
        elif word_count > self.profile.max_words - 10:
            warnings.append(f"{step_name}: Approaching maximum length")

        # CTA question check
        question_count = self._count_questions(step)
        if question_count < self.profile.min_cta_questions:
            errors.append(f"{step_name}: Missing CTA question")
        elif question_count > self.profile.max_cta_questions:
            warnings.append(f"{step_name}: Multiple questions (may be okay)")

        # Taboo phrase check
        taboo_found = self._contains_any(step, self.profile.taboo_phrases)
        if taboo_found:
            errors.append(f"{step_name}: Contains taboo phrases: {taboo_found}")

        # Signature check
        if not self._check_signature(step):
            errors.append(f"{step_name}: Missing or invalid signature")

        # Spam pattern checks
        spam_patterns = [
            r"(?i)dear\s+\w+",  # Dear [Name] - too formal
            r"(?i)to\s+whom\s+it\s+may\s+concern",
            r"(?i)valued\s+customer",
            r"(?i)limited\s+time\s+offer",
            r"(?i)act\s+now",
            r"(?i)urgent",
            r"(?i)congratulations.*?won",
        ]

        for pattern in spam_patterns:
            if re.search(pattern, step):
                warnings.append(f"{step_name}: Possible spam pattern detected")

        return ValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metrics={
                "word_count": word_count,
                "question_count": question_count,
            },
        )

    # Subject-line banned phrases / patterns (case-insensitive).
    SUBJECT_BANNED_PHRASES = ("quick question", "following up")

    def validate_subject(
        self, subject: str, subject_name: str
    ) -> ValidationResult:
        """Validate a single subject line (presence, banned phrases, format)."""
        errors: list[str] = []
        warnings: list[str] = []

        text = (subject or "").strip()
        if not text:
            errors.append(f"{subject_name}: Missing subject line")
            return ValidationResult(passed=False, errors=errors, warnings=warnings)

        lower = text.lower()
        for phrase in self.SUBJECT_BANNED_PHRASES:
            if phrase in lower:
                errors.append(
                    f"{subject_name}: Contains banned phrase '{phrase}'"
                )

        # "Re:" prefix (case-insensitive, tolerate surrounding space).
        if re.match(r"^\s*re\s*:", text, flags=re.IGNORECASE):
            errors.append(f"{subject_name}: Must not start with 'Re:'")

        # Emoji / non-BMP pictograph check (very conservative: flag any character
        # outside basic Latin + common punctuation ranges commonly found in
        # English subject lines).
        if any(ord(ch) > 0x2BFF for ch in text):
            errors.append(f"{subject_name}: Contains emoji or pictograph")

        word_count = len(text.split())
        if word_count < 4:
            errors.append(
                f"{subject_name}: Too short ({word_count} words, min 4)"
            )
        elif word_count > 8:
            errors.append(
                f"{subject_name}: Too long ({word_count} words, max 8)"
            )

        return ValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metrics={"word_count": word_count},
        )

    def validate_sequence(
        self, sequence: dict[str, str], strict: bool = True
    ) -> GeneratedSequence:
        """Validate a full 3-step sequence and return with metadata."""
        all_errors = []
        all_warnings = []
        total_words = 0

        steps = ["step_1", "step_2", "step_3"]
        validated_steps = {}

        for step_name in steps:
            step_text = sequence.get(step_name, "")
            result = self.validate_step(step_text, step_name, strict=strict)

            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            total_words += result.metrics.get("word_count", 0)

            validated_steps[step_name] = step_text

        # Subject line validation
        subjects = ["subject_1", "subject_2", "subject_3"]
        validated_subjects: dict[str, str] = {}
        for subject_name in subjects:
            subject_text = sequence.get(subject_name, "")
            result = self.validate_subject(subject_text, subject_name)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            validated_subjects[subject_name] = subject_text

        return GeneratedSequence(
            step_1=validated_steps["step_1"],
            step_2=validated_steps["step_2"],
            step_3=validated_steps["step_3"],
            subject_1=validated_subjects["subject_1"],
            subject_2=validated_subjects["subject_2"],
            subject_3=validated_subjects["subject_3"],
            voice_profile_version=self.profile.version,
            generation_method="static",  # Will be "rag" when RAG is implemented
            validation_passed=len(all_errors) == 0,
            validation_errors=all_errors,
        )


class JSONValidator:
    """Validates LLM output structure."""

    REQUIRED_KEYS = [
        "step_1",
        "step_2",
        "step_3",
        "subject_1",
        "subject_2",
        "subject_3",
    ]

    @classmethod
    def validate_structure(cls, data: dict[str, Any]) -> ValidationResult:
        """Validate that output has required structure."""
        errors = []

        for key in cls.REQUIRED_KEYS:
            if key not in data:
                errors.append(f"Missing required key: {key}")
            elif not isinstance(data[key], str):
                errors.append(f"Key {key} must be a string")
            elif not data[key].strip():
                errors.append(f"Key {key} cannot be empty")

        return ValidationResult(
            passed=len(errors) == 0,
            errors=errors,
        )
