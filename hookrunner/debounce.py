"""Debounce support: prevent a hook from firing more than once within a
cooldown window (wall-clock based, persisted to disk)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

_STATE_DIR = Path(os.environ.get("HOOKRUNNER_DEBOUNCE_DIR", ".hookrunner_debounce"))

DEFAULT_WINDOW = 2.0  # seconds


class DebounceError(Exception):
    """Raised when debounce state cannot be read or written."""


def _state_path(hook_name: str, base: Optional[Path] = None) -> Path:
    directory = base if base is not None else _STATE_DIR
    safe = hook_name.replace(os.sep, "_").replace("/", "_")
    return directory / f"{safe}.debounce.json"


def get_last_fired(hook_name: str, base: Optional[Path] = None) -> Optional[float]:
    """Return the wall-clock timestamp of the last fire, or None."""
    path = _state_path(hook_name, base)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return float(data["last_fired"])
    except Exception as exc:
        raise DebounceError(f"Cannot read debounce state for {hook_name!r}: {exc}") from exc


def record_fired(hook_name: str, base: Optional[Path] = None, timestamp: Optional[float] = None) -> None:
    """Persist the current wall-clock time as the last-fired timestamp."""
    if not hook_name:
        raise DebounceError("hook_name must not be empty")
    path = _state_path(hook_name, base)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"last_fired": timestamp if timestamp is not None else time.time()}))
    except OSError as exc:
        raise DebounceError(f"Cannot write debounce state for {hook_name!r}: {exc}") from exc


def is_debounced(hook_name: str, window: float = DEFAULT_WINDOW, base: Optional[Path] = None) -> bool:
    """Return True if the hook fired within *window* seconds."""
    last = get_last_fired(hook_name, base)
    if last is None:
        return False
    return (time.time() - last) < window


def get_window(config: dict, hook_name: str) -> float:
    """Resolve debounce window from config (hook-level overrides global)."""
    hook_cfg = config.get("hooks", {}).get(hook_name, {})
    if "debounce" in hook_cfg:
        return float(hook_cfg["debounce"])
    global_cfg = config.get("debounce", {})
    if isinstance(global_cfg, dict):
        return float(global_cfg.get("window", DEFAULT_WINDOW))
    if isinstance(global_cfg, (int, float)):
        return float(global_cfg)
    return DEFAULT_WINDOW


def reset(hook_name: str, base: Optional[Path] = None) -> None:
    """Remove persisted debounce state for *hook_name*."""
    path = _state_path(hook_name, base)
    if path.exists():
        path.unlink()
