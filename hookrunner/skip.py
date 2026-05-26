"""Skip logic for hookrunner — allows commands or entire hooks to be skipped
based on environment variables or explicit config flags."""

from __future__ import annotations

import os
from typing import Any


class SkipError(Exception):
    """Raised when skip configuration is invalid."""


# Environment variable that unconditionally skips all hooks when set to '1' / 'true'
_SKIP_ALL_ENV = "HOOKRUNNER_SKIP"


def is_skip_all(env: dict[str, str] | None = None) -> bool:
    """Return True if the global skip env-var is set to a truthy value."""
    env = env if env is not None else dict(os.environ)
    val = env.get(_SKIP_ALL_ENV, "").strip().lower()
    return val in ("1", "true", "yes")


def _get_skip_flag(mapping: dict[str, Any], key: str) -> bool | None:
    """Extract an optional boolean 'skip' flag from *mapping* under *key*."""
    section = mapping.get(key)
    if not isinstance(section, dict):
        return None
    raw = section.get("skip")
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes")
    raise SkipError(
        f"Invalid 'skip' value under '{key}': expected bool or string, got {type(raw).__name__!r}"
    )


def should_skip_hook(hook_name: str, config: dict[str, Any]) -> bool:
    """Return True if the named hook should be skipped entirely.

    Priority:
    1. Global ``skip: true`` at the top level.
    2. Per-hook ``skip: true`` inside the hook's config block.
    """
    top_skip = config.get("skip")
    if isinstance(top_skip, bool) and top_skip:
        return True
    if isinstance(top_skip, str) and top_skip.strip().lower() in ("1", "true", "yes"):
        return True

    flag = _get_skip_flag(config.get("hooks", {}), hook_name)
    return bool(flag)


def should_skip_command(command: dict[str, Any]) -> bool:
    """Return True if a single command entry carries ``skip: true``."""
    if not isinstance(command, dict):
        raise SkipError(f"command must be a dict, got {type(command).__name__!r}")
    raw = command.get("skip")
    if raw is None:
        return False
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes")
    raise SkipError(
        f"Invalid 'skip' value in command: expected bool or string, got {type(raw).__name__!r}"
    )


def filter_commands(
    commands: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a new list with any commands marked ``skip: true`` removed."""
    return [cmd for cmd in commands if not should_skip_command(cmd)]
