"""Hook command priority ordering — sort and filter commands by priority level."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

DEFAULT_PRIORITY = 50
MIN_PRIORITY = 0
MAX_PRIORITY = 100


class PriorityError(Exception):
    """Raised when priority configuration is invalid."""


def get_priority(command: Dict[str, Any]) -> int:
    """Return the numeric priority for a command entry.

    Priority must be an integer between 0 (lowest) and 100 (highest).
    Defaults to 50 when not specified.
    """
    raw = command.get("priority", DEFAULT_PRIORITY)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise PriorityError(
            f"priority must be an integer, got {raw!r}"
        ) from exc
    if not (MIN_PRIORITY <= value <= MAX_PRIORITY):
        raise PriorityError(
            f"priority must be between {MIN_PRIORITY} and {MAX_PRIORITY}, got {value}"
        )
    return value


def sort_commands(
    commands: List[Dict[str, Any]],
    *,
    reverse: bool = True,
) -> List[Dict[str, Any]]:
    """Return commands sorted by priority.

    Higher priority values run first by default (reverse=True).
    Commands with equal priority preserve their original relative order
    (stable sort).
    """
    return sorted(commands, key=get_priority, reverse=reverse)


def filter_by_min_priority(
    commands: List[Dict[str, Any]],
    min_priority: int,
) -> List[Dict[str, Any]]:
    """Return only commands whose priority is >= *min_priority*."""
    if not (MIN_PRIORITY <= min_priority <= MAX_PRIORITY):
        raise PriorityError(
            f"min_priority must be between {MIN_PRIORITY} and {MAX_PRIORITY}"
        )
    return [cmd for cmd in commands if get_priority(cmd) >= min_priority]


def priority_config_for_hook(
    config: Dict[str, Any],
    hook_name: str,
) -> Optional[int]:
    """Return the minimum-priority threshold configured for *hook_name*, or None.

    Looks first under hooks.<hook_name>.min_priority, then global min_priority.
    """
    hooks = config.get("hooks", {})
    hook_cfg = hooks.get(hook_name, {})
    raw = hook_cfg.get("min_priority", config.get("min_priority"))
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise PriorityError(
            f"min_priority must be an integer, got {raw!r}"
        ) from exc
    if not (MIN_PRIORITY <= value <= MAX_PRIORITY):
        raise PriorityError(
            f"min_priority must be between {MIN_PRIORITY} and {MAX_PRIORITY}, got {value}"
        )
    return value
