from __future__ import annotations

import json
from typing import Any

import requests

from .config import Settings


class OpenRouterClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def generate(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.7
    ) -> str:
        if not self._settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        payload: dict[str, Any] = {
            "model": self._settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self._settings.openrouter_http_referer,
            "X-OpenRouter-Title": self._settings.openrouter_title,
        }
        response = requests.post(
            f"{self._settings.openrouter_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload),
            headers=headers,
            timeout=90,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"OpenRouter error {response.status_code}: {response.text}"
            )

        body = response.json()
        choices = body.get("choices", [])
        if not choices:
            raise RuntimeError("OpenRouter returned no choices")

        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not isinstance(content, str):
            raise RuntimeError("OpenRouter returned non-text content")
        return content.strip()
