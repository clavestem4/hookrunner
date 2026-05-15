"""Retry logic for hook commands that fail transiently."""

import time
from typing import Callable, Optional


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""


DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_DELAY_SECONDS = 1.0
DEFAULT_BACKOFF_FACTOR = 2.0


def retry(
    fn: Callable,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    delay: float = DEFAULT_DELAY_SECONDS,
    backoff: float = DEFAULT_BACKOFF_FACTOR,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
):
    """Call *fn* repeatedly until it succeeds or attempts are exhausted.

    Args:
        fn: Zero-argument callable to invoke.
        max_attempts: Maximum number of total attempts (>= 1).
        delay: Initial wait in seconds between attempts.
        backoff: Multiplier applied to *delay* after each failure.
        exceptions: Tuple of exception types that trigger a retry.
        on_retry: Optional callback(attempt_number, exception) invoked before
                  each retry sleep.

    Returns:
        The return value of *fn* on success.

    Raises:
        RetryError: When *fn* raises a matching exception on every attempt.
        ValueError: When *max_attempts* is less than 1.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    current_delay = delay
    last_exc: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except exceptions as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt == max_attempts:
                break
            if on_retry is not None:
                on_retry(attempt, exc)
            time.sleep(current_delay)
            current_delay *= backoff

    raise RetryError(
        f"All {max_attempts} attempt(s) failed. Last error: {last_exc}"
    ) from last_exc


def retry_config_for_hook(hook_config: dict) -> dict:
    """Extract retry settings from a hook's config dict.

    Supported keys under each hook entry:
        retry_attempts (int)
        retry_delay   (float, seconds)
        retry_backoff (float, multiplier)

    Returns a dict suitable for passing as **kwargs to :func:`retry`.
    """
    return {
        "max_attempts": int(hook_config.get("retry_attempts", DEFAULT_MAX_ATTEMPTS)),
        "delay": float(hook_config.get("retry_delay", DEFAULT_DELAY_SECONDS)),
        "backoff": float(hook_config.get("retry_backoff", DEFAULT_BACKOFF_FACTOR)),
    }
