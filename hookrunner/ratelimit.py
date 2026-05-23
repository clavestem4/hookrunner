"""Rate limiting for hook execution — prevents hooks from running more
than N times within a rolling time window."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List, Optional


class RateLimitError(Exception):
    """Raised when a rate limit is exceeded or state cannot be managed."""


def _state_path(name: str, base: Optional[Path] = None) -> Path:
    if not name:
        raise RateLimitError("Hook name must not be empty")
    safe = name.replace(os.sep, "_").replace("/", "_")
    root = base or Path.cwd() / ".hookrunner" / "ratelimit"
    return root / f"{safe}.json"


def _load_timestamps(path: Path) -> List[float]:
    """Return stored timestamps, or empty list if file is absent."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, list):
            raise RateLimitError(f"Corrupt rate-limit state file: {path}")
        return [float(ts) for ts in data]
    except (json.JSONDecodeError, ValueError) as exc:
        raise RateLimitError(f"Corrupt rate-limit state file: {path}") from exc


def _save_timestamps(path: Path, timestamps: List[float]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(timestamps))
    except OSError as exc:
        raise RateLimitError(f"Cannot write rate-limit state to {path}") from exc


def is_rate_limited(
    name: str,
    max_runs: int,
    window_seconds: float,
    base: Optional[Path] = None,
    _now: Optional[float] = None,
) -> bool:
    """Return True if *name* has already fired *max_runs* times within the window."""
    if max_runs <= 0:
        return False
    now = _now if _now is not None else time.monotonic()
    path = _state_path(name, base)
    timestamps = _load_timestamps(path)
    recent = [ts for ts in timestamps if now - ts < window_seconds]
    return len(recent) >= max_runs


def record_run(
    name: str,
    window_seconds: float,
    base: Optional[Path] = None,
    _now: Optional[float] = None,
) -> None:
    """Record that *name* fired right now, pruning timestamps outside the window."""
    now = _now if _now is not None else time.monotonic()
    path = _state_path(name, base)
    timestamps = _load_timestamps(path)
    recent = [ts for ts in timestamps if now - ts < window_seconds]
    recent.append(now)
    _save_timestamps(path, recent)


def reset(name: str, base: Optional[Path] = None) -> None:
    """Clear all recorded timestamps for *name*."""
    path = _state_path(name, base)
    if path.exists():
        path.unlink()


def rate_limit_config_for_hook(config: dict, hook_name: str) -> dict:
    """Extract rate-limit settings for *hook_name* from a loaded config dict.

    Returns a dict with keys ``max_runs`` and ``window_seconds`` (both int/float),
    or an empty dict when no rate-limit is configured.
    """
    hook_cfg = config.get("hooks", {}).get(hook_name, {})
    rl = hook_cfg.get("rate_limit") or config.get("rate_limit") or {}
    if not rl:
        return {}
    try:
        return {
            "max_runs": int(rl["max_runs"]),
            "window_seconds": float(rl["window_seconds"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise RateLimitError(f"Invalid rate_limit config for hook '{hook_name}': {exc}") from exc
