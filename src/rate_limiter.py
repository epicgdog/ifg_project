"""Thread-safe token bucket rate limiters for external API providers.

Each limiter is a module-level singleton so all pipeline threads share the
same bucket. Callers just do ``APOLLO_LIMITER.acquire()`` before an API call —
if the bucket is exhausted the call blocks until a token is available.

Token bucket math:
  - Tokens refill continuously at `rpm / 60` tokens per second.
  - `burst` caps how many tokens can accumulate (prevents gorging after idle).
  - One HTTP request costs one token.

Conservative limits (stay ~10% below real API limits to absorb clock skew):
  - Apollo:      45 req/min  (typical paid plan: 50/min)
  - Apify:       12 req/min  (actor concurrency is the real limit; this throttles start rate)
  - OpenRouter:  40 req/min  (DeepSeek V3 on OpenRouter; raise if you upgrade tier)
"""
from __future__ import annotations

import threading
import time


class TokenBucketLimiter:
    """Thread-safe token bucket rate limiter.

    Args:
        rpm:   Maximum requests per minute.
        burst: Maximum tokens that can accumulate while idle. Defaults to
               10% of rpm (min 1) so a burst of idle threads can't flood
               the API after a quiet period.
    """

    def __init__(self, rpm: int, burst: int | None = None) -> None:
        self._rate = rpm / 60.0              # tokens per second
        self._burst = burst or max(1, rpm // 10)
        self._tokens = float(self._burst)    # start full
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> None:
        """Block until *tokens* are available, then consume them."""
        with self._lock:
            self._refill()
            if self._tokens < tokens:
                deficit = tokens - self._tokens
                sleep_time = deficit / self._rate
                # Release lock while sleeping so other threads can refill.
                self._lock.release()
                try:
                    time.sleep(sleep_time)
                finally:
                    self._lock.acquire()
                self._refill()
            self._tokens -= tokens

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_refill = now

    @property
    def rpm(self) -> float:
        return self._rate * 60


# ---------------------------------------------------------------------------
# Singletons — one per external API, shared across all pipeline threads.
# ---------------------------------------------------------------------------

APOLLO_LIMITER = TokenBucketLimiter(rpm=45, burst=5)
APIFY_LIMITER = TokenBucketLimiter(rpm=12, burst=2)
OPENROUTER_LIMITER = TokenBucketLimiter(rpm=40, burst=4)
