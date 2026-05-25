"""hookrunner.validator – lightweight command-definition validator.

Checks individual command entries from a hook config and emits
ValidationWarning objects for suspicious or unknown fields.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from typing import List, Optional

_KNOWN_KEYS = {
    "run", "name", "env", "timeout", "retry", "tags", "priority",
    "depends_on", "condition", "on_branches", "on_files", "glob",
    "escalation", "cooldown",
}


@dataclass
class ValidationWarning:
    command: str
    message: str

    def __repr__(self) -> str:  # pragma: no cover
        return f"ValidationWarning(command={self.command!r}, message={self.message!r})"

    def __str__(self) -> str:
        return f"[{self.command}] {self.message}"


def _extract_executable(run: str) -> str:
    """Return the executable portion of a run string."""
    if not run:
        return ""
    # Strip leading 'env VAR=val …' prefix
    run = run.strip()
    parts = run.split()
    idx = 0
    while idx < len(parts) and "=" in parts[idx]:
        idx += 1
    return parts[idx] if idx < len(parts) else ""


def validate_command(
    command: dict,
    name: str = "<unnamed>",
) -> List[ValidationWarning]:
    """Validate a single command dict and return any warnings found."""
    warnings: List[ValidationWarning] = []

    # Unknown keys
    for key in command:
        if key not in _KNOWN_KEYS:
            warnings.append(ValidationWarning(name, f"unknown key '{key}'"))

    # Missing 'run'
    run = command.get("run")
    if not run:
        warnings.append(ValidationWarning(name, "missing 'run' field"))
        return warnings

    if not isinstance(run, str):
        warnings.append(ValidationWarning(name, "'run' must be a string"))
        return warnings

    # Executable on PATH check (best-effort)
    exe = _extract_executable(run)
    if exe and not exe.startswith((".", "/")) and shutil.which(exe) is None:
        warnings.append(ValidationWarning(name, f"executable '{exe}' not found on PATH"))

    return warnings


def validate_hook_commands(
    commands: list,
    hook_name: str = "<hook>",
) -> List[ValidationWarning]:
    """Validate all commands for a hook and return aggregated warnings."""
    all_warnings: List[ValidationWarning] = []
    for cmd in commands:
        if not isinstance(cmd, dict):
            continue
        name = cmd.get("name") or hook_name
        all_warnings.extend(validate_command(cmd, name=name))
    return all_warnings
