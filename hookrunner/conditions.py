"""Conditional execution support for hook commands.

Allows commands to declare run conditions (e.g. only on CI, only when a file
exists, only when an env var is set) and skips them when conditions are unmet.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConditionsError(Exception):
    """Raised when a condition block is malformed."""


_TRUTHY = {"1", "true", "yes", "on"}


def _env_set(name: str) -> bool:
    """Return True when *name* is present and non-empty in the environment."""
    return bool(os.environ.get(name, "").strip())


def _env_equals(name: str, value: str) -> bool:
    """Return True when env var *name* equals *value* (case-insensitive)."""
    return os.environ.get(name, "").strip().lower() == value.strip().lower()


def _file_exists(path: str) -> bool:
    """Return True when *path* exists on the filesystem."""
    return Path(path).exists()


def evaluate_condition(condition: Dict[str, Any]) -> bool:
    """Evaluate a single condition dict and return whether it is satisfied.

    Supported condition types:
        - ``env_set: VAR_NAME``          – env var is present and non-empty
        - ``env_equals: {var: V, value: X}`` – env var equals a specific value
        - ``file_exists: /some/path``    – path exists on disk
        - ``ci: true``                   – running inside a CI environment

    Raises:
        ConditionsError: if the condition dict is empty or uses an unknown key.
    """
    if not condition:
        raise ConditionsError("Empty condition block")

    key = next(iter(condition))
    val = condition[key]

    if key == "env_set":
        if not isinstance(val, str) or not val.strip():
            raise ConditionsError("env_set requires a non-empty string var name")
        return _env_set(val)

    if key == "env_equals":
        if not isinstance(val, dict) or "var" not in val or "value" not in val:
            raise ConditionsError("env_equals requires {var: ..., value: ...}")
        return _env_equals(str(val["var"]), str(val["value"]))

    if key == "file_exists":
        if not isinstance(val, str) or not val.strip():
            raise ConditionsError("file_exists requires a non-empty path string")
        return _file_exists(val)

    if key == "ci":
        is_ci = _env_set("CI") or _env_set("CONTINUOUS_INTEGRATION")
        expected = str(val).lower() in _TRUTHY
        return is_ci == expected

    raise ConditionsError(f"Unknown condition type: '{key}'")


def command_should_run(
    command: Dict[str, Any],
    conditions_key: str = "conditions",
) -> bool:
    """Return True when all conditions for *command* are satisfied.

    If the command has no conditions block the command always runs.

    Args:
        command: A command dict from the hook config (may contain a
                 ``conditions`` list of condition dicts).
        conditions_key: Config key to look up (default: ``"conditions"``).

    Returns:
        ``True`` if every condition passes (or none are defined).

    Raises:
        ConditionsError: if any condition block is malformed.
    """
    raw: Optional[List[Dict[str, Any]]] = command.get(conditions_key)
    if not raw:
        return True
    if not isinstance(raw, list):
        raise ConditionsError("'conditions' must be a list of condition dicts")
    return all(evaluate_condition(c) for c in raw)
