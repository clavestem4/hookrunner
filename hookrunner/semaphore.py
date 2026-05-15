"""Concurrency limiter — prevents more than N hook processes running simultaneously."""

from __future__ import annotations

import os
import time
import json
import tempfile
from pathlib import Path
from typing import Optional

SEMAPHORE_DIR = Path(tempfile.gettempdir()) / "hookrunner_semaphores"
DEFAULT_MAX_WORKERS = 4
DEFAULT_POLL_INTERVAL = 0.1  # seconds


class SemaphoreError(Exception):
    """Raised when the semaphore cannot be acquired or released."""


def _semaphore_path(name: str) -> Path:
    SEMAPHORE_DIR.mkdir(parents=True, exist_ok=True)
    safe = name.replace("/", "_").replace("\\", "_")
    return SEMAPHORE_DIR / f"{safe}.sem.json"


def _read_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"slots": []}


def _write_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state))


def acquire(name: str, max_workers: int = DEFAULT_MAX_WORKERS,
            timeout: Optional[float] = None,
            poll_interval: float = DEFAULT_POLL_INTERVAL) -> int:
    """Acquire a semaphore slot for *name*. Returns the acquired slot id.

    Raises SemaphoreError if *timeout* is exceeded.
    """
    path = _semaphore_path(name)
    deadline = None if timeout is None else time.monotonic() + timeout
    pid = os.getpid()

    while True:
        state = _read_state(path)
        # Evict stale PIDs that no longer exist
        state["slots"] = [s for s in state["slots"] if _pid_alive(s)]
        if len(state["slots"]) < max_workers:
            state["slots"].append(pid)
            _write_state(path, state)
            return pid
        if deadline is not None and time.monotonic() >= deadline:
            raise SemaphoreError(
                f"Could not acquire semaphore '{name}' within {timeout}s "
                f"(max_workers={max_workers})"
            )
        time.sleep(poll_interval)


def release(name: str, slot_id: int) -> None:
    """Release a previously acquired slot."""
    path = _semaphore_path(name)
    state = _read_state(path)
    try:
        state["slots"].remove(slot_id)
    except ValueError:
        raise SemaphoreError(
            f"Slot {slot_id} not found in semaphore '{name}'; already released?"
        )
    _write_state(path, state)


def current_count(name: str) -> int:
    """Return the number of active slots for *name*."""
    path = _semaphore_path(name)
    state = _read_state(path)
    live = [s for s in state["slots"] if _pid_alive(s)]
    return len(live)


def reset(name: str) -> None:
    """Clear all slots for *name* (useful in tests)."""
    path = _semaphore_path(name)
    if path.exists():
        path.unlink()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
