"""Lockfile support to prevent concurrent hook execution for the same hook name."""

import os
import time
from pathlib import Path


class LockfileError(Exception):
    """Raised when a lockfile operation fails."""


DEFAULT_LOCK_DIR = Path(".hookrunner") / "locks"
DEFAULT_TIMEOUT = 30  # seconds


def _lock_path(hook_name: str, base_dir: Path = DEFAULT_LOCK_DIR) -> Path:
    if not hook_name or not hook_name.strip():
        raise LockfileError("hook_name must be a non-empty string")
    safe = hook_name.replace(os.sep, "_").replace("/", "_")
    return base_dir / f"{safe}.lock"


def acquire(hook_name: str, base_dir: Path = DEFAULT_LOCK_DIR, timeout: int = DEFAULT_TIMEOUT) -> int:
    """Acquire a lock for *hook_name*. Returns the PID written to the lock file.

    Raises LockfileError if the lock cannot be acquired within *timeout* seconds.
    """
    path = _lock_path(hook_name, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as fh:
                fh.write(str(pid))
            return pid
        except FileExistsError:
            # Check if the owning process is still alive
            try:
                owner = int(path.read_text().strip())
                os.kill(owner, 0)  # signal 0 — just checks existence
            except (ValueError, ProcessLookupError, PermissionError):
                # Stale lock — remove and retry immediately
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                continue
            time.sleep(0.1)
    raise LockfileError(
        f"Could not acquire lock for '{hook_name}' within {timeout}s (lock: {path})"
    )


def release(hook_name: str, base_dir: Path = DEFAULT_LOCK_DIR) -> None:
    """Release the lock for *hook_name*.

    Raises LockfileError if the lock file does not exist or is owned by another PID.
    """
    path = _lock_path(hook_name, base_dir)
    if not path.exists():
        raise LockfileError(f"No lock file found for '{hook_name}' at {path}")
    try:
        owner = int(path.read_text().strip())
    except (ValueError, OSError) as exc:
        raise LockfileError(f"Corrupt lock file for '{hook_name}': {exc}") from exc
    if owner != os.getpid():
        raise LockfileError(
            f"Lock for '{hook_name}' is owned by PID {owner}, not {os.getpid()}"
        )
    path.unlink(missing_ok=True)


def is_locked(hook_name: str, base_dir: Path = DEFAULT_LOCK_DIR) -> bool:
    """Return True if a live lock exists for *hook_name*."""
    path = _lock_path(hook_name, base_dir)
    if not path.exists():
        return False
    try:
        owner = int(path.read_text().strip())
        os.kill(owner, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False
