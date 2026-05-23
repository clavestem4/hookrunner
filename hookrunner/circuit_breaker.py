"""Circuit breaker for hook commands — stops repeated execution after consecutive failures."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

CIRCUIT_BREAKER_DIR = ".hookrunner/circuit_breaker"
_DEFAULT_THRESHOLD = 3
_DEFAULT_RESET_AFTER = 300  # seconds


class CircuitBreakerError(Exception):
    """Raised when the circuit breaker rejects execution or encounters a state error."""


def _state_path(name: str, base: Optional[Path] = None) -> Path:
    if not name:
        raise CircuitBreakerError("Circuit breaker name must not be empty")
    safe = name.replace(os.sep, "__")
    root = base or Path.cwd()
    return root / CIRCUIT_BREAKER_DIR / f"{safe}.json"


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {"failures": 0, "opened_at": None}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise CircuitBreakerError(f"Corrupt circuit breaker state at {path}: {exc}") from exc


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state))


def is_open(name: str, threshold: int = _DEFAULT_THRESHOLD,
            reset_after: int = _DEFAULT_RESET_AFTER,
            base: Optional[Path] = None) -> bool:
    """Return True if the circuit is open (i.e. hook should be skipped)."""
    path = _state_path(name, base)
    state = _load_state(path)
    opened_at = state.get("opened_at")
    if opened_at is None:
        return False
    if time.monotonic() - opened_at >= reset_after:
        _save_state(path, {"failures": 0, "opened_at": None})
        return False
    return state.get("failures", 0) >= threshold


def record_failure(name: str, threshold: int = _DEFAULT_THRESHOLD,
                   base: Optional[Path] = None) -> int:
    """Record a failure; open the circuit when threshold is reached. Returns failure count."""
    path = _state_path(name, base)
    state = _load_state(path)
    failures = state.get("failures", 0) + 1
    opened_at = state.get("opened_at")
    if failures >= threshold and opened_at is None:
        opened_at = time.monotonic()
    _save_state(path, {"failures": failures, "opened_at": opened_at})
    return failures


def record_success(name: str, base: Optional[Path] = None) -> None:
    """Reset the circuit breaker state after a successful run."""
    path = _state_path(name, base)
    _save_state(path, {"failures": 0, "opened_at": None})


def reset(name: str, base: Optional[Path] = None) -> None:
    """Manually reset the circuit breaker state."""
    path = _state_path(name, base)
    if path.exists():
        path.unlink()
