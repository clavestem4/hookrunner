"""Throttle repeated hook executions within a cooldown window."""

import time
from typing import Dict, Optional


class ThrottleError(Exception):
    """Raised when a throttle operation fails."""


_last_run: Dict[str, float] = {}


def get_last_run(hook_name: str) -> Optional[float]:
    """Return the timestamp of the last run for *hook_name*, or None."""
    return _last_run.get(hook_name)


def record_run(hook_name: str, timestamp: Optional[float] = None) -> float:
    """Record that *hook_name* ran at *timestamp* (defaults to now).

    Returns the recorded timestamp.
    """
    if not hook_name:
        raise ThrottleError("hook_name must be a non-empty string")
    ts = timestamp if timestamp is not None else time.monotonic()
    _last_run[hook_name] = ts
    return ts


def is_throttled(hook_name: str, cooldown: float) -> bool:
    """Return True if *hook_name* was run within the last *cooldown* seconds.

    Args:
        hook_name: Identifier for the hook (e.g. ``"pre-commit"``).
        cooldown:  Minimum seconds that must pass between executions.

    Raises:
        ThrottleError: If *cooldown* is negative.
    """
    if cooldown < 0:
        raise ThrottleError(f"cooldown must be >= 0, got {cooldown}")
    last = get_last_run(hook_name)
    if last is None:
        return False
    return (time.monotonic() - last) < cooldown


def reset(hook_name: Optional[str] = None) -> None:
    """Clear throttle state.

    If *hook_name* is given, only that entry is removed; otherwise the
    entire in-memory store is cleared.
    """
    if hook_name is not None:
        _last_run.pop(hook_name, None)
    else:
        _last_run.clear()
