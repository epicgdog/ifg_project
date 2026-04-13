from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

from .config import Settings
from .rate_limiter import OPENROUTER_LIMITER


logger = logging.getLogger(__name__)


# HTTP status codes that are safe to retry (transient server / rate-limit errors).
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Exponential backoff schedule in seconds: 1s -> 2s -> 4s between retries.
_RETRY_DELAYS = (1.0, 2.0, 4.0)


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
        url = f"{self._settings.openrouter_base_url.rstrip('/')}/chat/completions"

        response = self._post_with_retry(url, payload, headers)

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

    def _post_with_retry(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> requests.Response:
        """POST with 3 retries and exponential backoff (1s, 2s, 4s).

        Retries on connection errors, timeouts, and HTTP 429/500/502/503/504.
        Does NOT retry on 400/401/403 (client errors) -- these are returned
        immediately so the caller can surface the real problem.
        """
        last_exc: Exception | None = None
        last_response: requests.Response | None = None

        # 1 initial attempt + len(_RETRY_DELAYS) retries = 4 total attempts,
        # which gives the 3 retries the task specifies.
        total_attempts = 1 + len(_RETRY_DELAYS)

        for attempt in range(total_attempts):
            OPENROUTER_LIMITER.acquire()
            try:
                response = requests.post(
                    url,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=90,
                )
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                last_exc = e
                last_response = None
                if attempt < len(_RETRY_DELAYS):
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning(
                        "OpenRouter request failed (%s); retrying in %.1fs "
                        "(attempt %d/%d)",
                        type(e).__name__,
                        delay,
                        attempt + 1,
                        total_attempts,
                    )
                    time.sleep(delay)
                    continue
                break

            # Non-retryable client errors: return immediately.
            if response.status_code in (400, 401, 403):
                return response

            # Retryable server / rate-limit errors.
            if response.status_code in _RETRYABLE_STATUS and attempt < len(
                _RETRY_DELAYS
            ):
                delay = _RETRY_DELAYS[attempt]
                logger.warning(
                    "OpenRouter returned HTTP %d; retrying in %.1fs "
                    "(attempt %d/%d)",
                    response.status_code,
                    delay,
                    attempt + 1,
                    total_attempts,
                )
                last_response = response
                time.sleep(delay)
                continue

            # Success, or a non-retryable status we should bubble up as-is.
            return response

        # Exhausted retries.
        if last_response is not None:
            return last_response
        assert last_exc is not None
        raise last_exc
