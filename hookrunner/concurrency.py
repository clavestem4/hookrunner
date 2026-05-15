"""High-level concurrency helpers used by the runner.

Wraps hookrunner.semaphore to provide a context-manager API and
reads concurrency settings from the hook config.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

from hookrunner.semaphore import (
    acquire,
    release,
    SemaphoreError,
)

DEFAULT_MAX_WORKERS = 4


class ConcurrencyError(Exception):
    """Raised when a concurrency limit cannot be satisfied."""


def get_max_workers(config: dict, hook_name: str) -> int:
    """Resolve max_workers for *hook_name* from *config*.

    Priority: hook-level > global > DEFAULT_MAX_WORKERS.
    """
    global_val = config.get("concurrency", {}).get("max_workers")
    hooks = config.get("hooks", {})
    hook_val = hooks.get(hook_name, {}).get("max_workers")
    raw = hook_val if hook_val is not None else global_val
    if raw is None:
        return DEFAULT_MAX_WORKERS
    try:
        val = int(raw)
    except (TypeError, ValueError) as exc:
        raise ConcurrencyError(
            f"Invalid max_workers value {raw!r} for hook '{hook_name}'"
        ) from exc
    if val < 1:
        raise ConcurrencyError(
            f"max_workers must be >= 1, got {val} for hook '{hook_name}'"
        )
    return val


@contextmanager
def concurrency_slot(
    hook_name: str,
    max_workers: int = DEFAULT_MAX_WORKERS,
    timeout: Optional[float] = None,
) -> Generator[int, None, None]:
    """Context manager that acquires a semaphore slot and releases it on exit.

    Raises ConcurrencyError if the slot cannot be acquired within *timeout*.
    """
    try:
        slot = acquire(hook_name, max_workers=max_workers, timeout=timeout)
    except SemaphoreError as exc:
        raise ConcurrencyError(str(exc)) from exc
    try:
        yield slot
    finally:
        try:
            release(hook_name, slot)
        except SemaphoreError:
            pass  # Already released or stale — safe to ignore on exit
