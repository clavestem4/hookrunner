"""Timeout support for hook command execution."""

import signal
import contextlib
from typing import Optional


class TimeoutError(Exception):  # noqa: A001
    """Raised when a hook command exceeds its allowed execution time."""

    def __init__(self, hook_name: str, command: str, seconds: int) -> None:
        self.hook_name = hook_name
        self.command = command
        self.seconds = seconds
        super().__init__(
            f"Hook '{hook_name}' command '{command}' timed out after {seconds}s"
        )


def _timeout_handler(signum, frame):
    raise TimeoutError.__new__(TimeoutError)


def get_timeout(config: dict, hook_name: str) -> Optional[int]:
    """Return timeout in seconds for a given hook, or None if not configured.

    Looks first at per-hook settings, then falls back to a global default.
    """
    hooks = config.get("hooks", {})
    hook_cfg = hooks.get(hook_name, {})
    if isinstance(hook_cfg, dict):
        timeout = hook_cfg.get("timeout")
        if timeout is not None:
            return int(timeout)
    global_timeout = config.get("settings", {}).get("timeout")
    if global_timeout is not None:
        return int(global_timeout)
    return None


@contextlib.contextmanager
def timeout_context(seconds: int, hook_name: str, command: str):
    """Context manager that raises TimeoutError if block exceeds *seconds*.

    Uses SIGALRM and is therefore only available on Unix-like systems.
    When *seconds* is 0 or negative the context manager is a no-op.
    """
    if seconds <= 0:
        yield
        return

    old_handler = signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(
        TimeoutError(hook_name, command, seconds)
    ))
    signal.alarm(seconds)
    try:
        yield
    except TimeoutError:
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
