"""Per-hook execution quota enforcement.

Tracks how many times a hook has run within a rolling time window and
rejects further executions once the configured limit is reached.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List, Optional

QUOTA_DIR = Path(os.environ.get("HOOKRUNNER_QUOTA_DIR", ".hookrunner/quota"))


class QuotaError(Exception):
    """Raised when a quota operation fails or the quota is exceeded."""


def _state_path(name: str, base: Path = QUOTA_DIR) -> Path:
    if not name:
        raise QuotaError("Hook name must not be empty.")
    safe = name.replace(os.sep, "_").replace("/", "_")
    return base / f"{safe}.quota.json"


def _load_timestamps(path: Path) -> List[float]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, list):
            raise QuotaError(f"Corrupt quota state: {path}")
        return [float(ts) for ts in data]
    except (json.JSONDecodeError, ValueError) as exc:
        raise QuotaError(f"Corrupt quota state: {path}") from exc


def _save_timestamps(path: Path, timestamps: List[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(timestamps))


def _window_timestamps(timestamps: List[float], window: int, now: float) -> List[float]:
    """Return only timestamps that fall within the rolling window."""
    cutoff = now - window
    return [ts for ts in timestamps if ts >= cutoff]


def is_quota_exceeded(
    name: str,
    limit: int,
    window: int,
    base: Path = QUOTA_DIR,
    _now: Optional[float] = None,
) -> bool:
    """Return True if *name* has reached *limit* executions within *window* seconds."""
    if limit <= 0:
        raise QuotaError("limit must be a positive integer.")
    if window <= 0:
        raise QuotaError("window must be a positive integer.")
    now = _now if _now is not None else time.monotonic()
    path = _state_path(name, base)
    timestamps = _window_timestamps(_load_timestamps(path), window, now)
    return len(timestamps) >= limit


def record_execution(
    name: str,
    base: Path = QUOTA_DIR,
    _now: Optional[float] = None,
) -> None:
    """Record a single execution of *name* at the current monotonic time."""
    if not name:
        raise QuotaError("Hook name must not be empty.")
    now = _now if _now is not None else time.monotonic()
    path = _state_path(name, base)
    timestamps = _load_timestamps(path)
    timestamps.append(now)
    _save_timestamps(path, timestamps)


def reset_quota(name: str, base: Path = QUOTA_DIR) -> None:
    """Clear all recorded executions for *name*."""
    path = _state_path(name, base)
    if path.exists():
        path.unlink()


def quota_config_for_hook(config: dict, hook_name: str) -> dict:
    """Extract quota settings for *hook_name* from a hookrunner config dict."""
    global_quota = config.get("quota", {})
    hook_cfg = config.get("hooks", {}).get(hook_name, {})
    hook_quota = hook_cfg.get("quota", {})
    merged = {**global_quota, **hook_quota}
    return merged
