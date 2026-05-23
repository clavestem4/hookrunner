"""Exponential back-off helper for hookrunner retry/rate-limit logic."""

from __future__ import annotations

import random
import time
from typing import Optional


class BackoffError(Exception):
    """Raised when back-off configuration is invalid."""


def compute_delay(
    attempt: int,
    base: float = 1.0,
    factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """Return the delay (seconds) for *attempt* (0-indexed).

    Args:
        attempt:   Zero-based attempt number (0 = first retry).
        base:      Initial delay in seconds.
        factor:    Multiplicative growth factor per attempt.
        max_delay: Upper bound on the computed delay.
        jitter:    When True, add uniform random jitter in [0, delay).

    Raises:
        BackoffError: If any numeric parameter is invalid.
    """
    if base <= 0:
        raise BackoffError(f"base must be positive, got {base!r}")
    if factor < 1:
        raise BackoffError(f"factor must be >= 1, got {factor!r}")
    if max_delay <= 0:
        raise BackoffError(f"max_delay must be positive, got {max_delay!r}")
    if attempt < 0:
        raise BackoffError(f"attempt must be >= 0, got {attempt!r}")

    delay = min(base * (factor ** attempt), max_delay)
    if jitter:
        delay = random.uniform(0, delay)
    return delay


def backoff_config_for_hook(
    config: dict,
    hook_name: str,
) -> dict:
    """Extract back-off settings for *hook_name* from a loaded config dict.

    Merges global ``backoff`` block with hook-level ``backoff`` overrides.
    Returns a dict with keys: base, factor, max_delay, jitter.
    """
    defaults = {
        "base": 1.0,
        "factor": 2.0,
        "max_delay": 60.0,
        "jitter": True,
    }
    global_block = config.get("backoff") or {}
    hooks_block = config.get("hooks") or {}
    hook_block = (hooks_block.get(hook_name) or {}).get("backoff") or {}

    merged = {**defaults, **global_block, **hook_block}
    return {
        "base": float(merged["base"]),
        "factor": float(merged["factor"]),
        "max_delay": float(merged["max_delay"]),
        "jitter": bool(merged["jitter"]),
    }


def sleep_with_backoff(
    attempt: int,
    base: float = 1.0,
    factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    _sleep: Optional[callable] = None,  # injectable for tests
) -> float:
    """Compute delay and sleep; return the actual delay used."""
    delay = compute_delay(
        attempt, base=base, factor=factor, max_delay=max_delay, jitter=jitter
    )
    (_sleep or time.sleep)(delay)
    return delay
