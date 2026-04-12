"""In-memory run state tracking for background pipeline jobs."""
from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RunState:
    run_id: str
    status: str = "pending"  # pending | running | done | error
    event_queue: queue.Queue = field(default_factory=queue.Queue)
    report: dict[str, Any] | None = None
    output_csv: str | None = None
    instantly_csv: str | None = None
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None


class RunRegistry:
    """Thread-safe registry for run state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, RunState] = {}

    def create(self) -> RunState:
        run_id = uuid.uuid4().hex[:12]
        state = RunState(run_id=run_id)
        with self._lock:
            self._runs[run_id] = state
        return state

    def get(self, run_id: str) -> RunState | None:
        with self._lock:
            return self._runs.get(run_id)

    def all(self) -> list[RunState]:
        with self._lock:
            return list(self._runs.values())


RUNS = RunRegistry()


def run_output_dir(run_id: str) -> Path:
    path = Path("out") / "runs" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path
