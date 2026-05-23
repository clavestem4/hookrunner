"""Cooldown: enforce a minimum wait between successive hook runs."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

COOLDOWN_DIR = Path(os.environ.get("HOOKRUNNER_COOLDOWN_DIR", ".hookrunner/cooldown"))


class CooldownError(Exception):
    """Raised when cooldown state cannot be read or written."""


def _state_path(name: str, base: Path = COOLDOWN_DIR) -> Path:
    if not name:
        raise CooldownError("Hook name must not be empty.")
    safe = name.replace(os.sep, "_").replace("/", "_")
    return base / f"{safe}.json"


def get_last_run(name: str, base: Path = COOLDOWN_DIR) -> float | None:
    """Return the timestamp of the last recorded run, or None."""
    path = _state_path(name, base)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return float(data["last_run"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise CooldownError(f"Corrupt cooldown state for '{name}': {exc}") from exc


def record_run(name: str, base: Path = COOLDOWN_DIR, *, timestamp: float | None = None) -> None:
    """Record the current time as the last run for *name*."""
    if not name:
        raise CooldownError("Hook name must not be empty.")
    path = _state_path(name, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = timestamp if timestamp is not None else time.monotonic()
    try:
        path.write_text(json.dumps({"last_run": ts}))
    except OSError as exc:
        raise CooldownError(f"Cannot write cooldown state for '{name}': {exc}") from exc


def is_cooling_down(name: str, period: float, base: Path = COOLDOWN_DIR) -> bool:
    """Return True if *name* was run within the last *period* seconds."""
    if period <= 0:
        return False
    last = get_last_run(name, base)
    if last is None:
        return False
    return (time.monotonic() - last) < period


def cooldown_period_for_hook(name: str, config: dict) -> float:
    """Extract the cooldown period (seconds) for *name* from *config*.

    Looks up ``hooks.<name>.cooldown`` then falls back to
    ``settings.cooldown_period``.  Returns 0 if neither is set.
    """
    hooks = config.get("hooks", {})
    hook_cfg = hooks.get(name, {})
    if "cooldown" in hook_cfg:
        return float(hook_cfg["cooldown"])
    settings = config.get("settings", {})
    return float(settings.get("cooldown_period", 0))


def reset(name: str, base: Path = COOLDOWN_DIR) -> None:
    """Remove the cooldown state for *name*, if it exists."""
    path = _state_path(name, base)
    if path.exists():
        path.unlink()
