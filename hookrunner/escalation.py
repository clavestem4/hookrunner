"""escalation.py — Per-hook failure escalation policy.

Supports configurable escalation levels (warn, error, fatal) that control
how hookrunner responds when a hook command exits with a non-zero status.
"""

from __future__ import annotations

from typing import Optional

__all__ = [
    "EscalationError",
    "EscalationLevel",
    "get_escalation_level",
    "should_abort",
    "should_warn",
    "escalation_config_for_hook",
]

_VALID_LEVELS = ("warn", "error", "fatal")
_DEFAULT_LEVEL = "error"


class EscalationError(Exception):
    """Raised when an escalation policy is misconfigured."""


class EscalationLevel:
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"


def get_escalation_level(
    command: dict,
    hook_config: dict,
    global_config: dict,
) -> str:
    """Return the resolved escalation level for a command.

    Resolution order: command-level > hook-level > global > default ("error").
    """
    level = (
        command.get("on_failure")
        or hook_config.get("on_failure")
        or global_config.get("on_failure")
        or _DEFAULT_LEVEL
    )
    level = str(level).lower().strip()
    if level not in _VALID_LEVELS:
        raise EscalationError(
            f"Invalid escalation level {level!r}. "
            f"Must be one of: {', '.join(_VALID_LEVELS)}"
        )
    return level


def should_abort(level: str) -> bool:
    """Return True if the escalation level should stop hook execution."""
    _validate_level(level)
    return level in (EscalationLevel.ERROR, EscalationLevel.FATAL)


def should_warn(level: str) -> bool:
    """Return True if the escalation level should emit a warning only."""
    _validate_level(level)
    return level == EscalationLevel.WARN


def escalation_config_for_hook(
    hook_name: str,
    config: dict,
) -> dict:
    """Extract the escalation sub-config relevant to *hook_name*.

    Returns a dict with keys ``on_failure`` at global and hook level.
    """
    global_level: Optional[str] = config.get("on_failure")
    hooks: dict = config.get("hooks", {})
    hook_cfg: dict = hooks.get(hook_name, {})
    hook_level: Optional[str] = hook_cfg.get("on_failure")
    return {
        "global": global_level,
        "hook": hook_level,
        "resolved": hook_level or global_level or _DEFAULT_LEVEL,
    }


def _validate_level(level: str) -> None:
    if level not in _VALID_LEVELS:
        raise EscalationError(
            f"Unknown escalation level {level!r}. "
            f"Expected one of: {', '.join(_VALID_LEVELS)}"
        )
