"""allowlist.py – Command allowlist enforcement for hookrunner.

Allows teams to restrict which executables / commands may be run inside
hooks.  When an allowlist is defined in the config, any command whose
resolved executable is not present in the list is blocked.
"""

from __future__ import annotations

import re
from typing import List, Optional


class AllowlistError(Exception):
    """Raised when an allowlist violation or configuration problem occurs."""


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _get_allowlist(config: dict, hook_name: Optional[str] = None) -> Optional[List[str]]:
    """Return the merged allowlist for *hook_name*, or the global one.

    Hook-level allowlist takes full precedence over the global list when
    both are present.  Returns *None* when no allowlist is configured.
    """
    if not isinstance(config, dict):
        return None

    global_list = config.get("allowlist") or []

    if hook_name:
        hooks = config.get("hooks", {})
        hook_cfg = hooks.get(hook_name, {}) if isinstance(hooks, dict) else {}
        hook_list = hook_cfg.get("allowlist") if isinstance(hook_cfg, dict) else None
        if hook_list is not None:
            return [str(e).strip() for e in hook_list if str(e).strip()]

    if global_list:
        return [str(e).strip() for e in global_list if str(e).strip()]

    return None


# ---------------------------------------------------------------------------
# Executable extraction (mirrors validator._extract_executable lightly)
# ---------------------------------------------------------------------------

_ENV_PREFIX = re.compile(r'^(?:[A-Z_][A-Z0-9_]*=\S*\s+)+')


def _extract_executable(command: str) -> str:
    """Return the executable token from *command* string."""
    command = command.strip()
    command = _ENV_PREFIX.sub("", command).strip()
    if not command:
        return ""
    token = command.split()[0]
    # strip leading path components so callers can use bare names
    return token.split("/")[-1]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_allowed(command: str, config: dict, hook_name: Optional[str] = None) -> bool:
    """Return *True* when *command* is permitted by the active allowlist.

    If no allowlist is configured the function always returns *True*.
    """
    allowlist = _get_allowlist(config, hook_name)
    if allowlist is None:
        return True
    executable = _extract_executable(command)
    return executable in allowlist


def filter_commands(
    commands: List[str],
    config: dict,
    hook_name: Optional[str] = None,
) -> List[str]:
    """Return only the commands permitted by the allowlist.

    Commands that are blocked are silently dropped.  Use *check_commands*
    when you need hard enforcement with an exception.
    """
    return [cmd for cmd in commands if is_allowed(cmd, config, hook_name)]


def check_commands(
    commands: List[str],
    config: dict,
    hook_name: Optional[str] = None,
) -> None:
    """Raise :class:`AllowlistError` if any command is not on the allowlist."""
    allowlist = _get_allowlist(config, hook_name)
    if allowlist is None:
        return
    for cmd in commands:
        executable = _extract_executable(cmd)
        if executable not in allowlist:
            raise AllowlistError(
                f"Command executable '{executable}' is not in the allowlist "
                f"for hook '{hook_name or 'global'}'. "
                f"Allowed: {allowlist}"
            )
