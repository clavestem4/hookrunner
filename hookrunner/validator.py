"""Hook script validator — checks commands in hook configs for common issues."""

import os
import shutil
from typing import List, Tuple


class ValidationWarning:
    def __init__(self, hook: str, command: str, message: str):
        self.hook = hook
        self.command = command
        self.message = message

    def __repr__(self):
        return f"ValidationWarning(hook={self.hook!r}, command={self.command!r}, message={self.message!r})"

    def __str__(self):
        return f"[{self.hook}] '{self.command}': {self.message}"


def _extract_executable(command: str) -> str:
    """Return the base executable name from a shell command string."""
    parts = command.strip().split()
    if not parts:
        return ""
    # Strip common shell prefixes
    skip = {"env", "sudo"}
    for part in parts:
        if part not in skip:
            return os.path.basename(part)
    return os.path.basename(parts[-1])


def validate_hook_commands(
    config: dict,
) -> Tuple[bool, List[ValidationWarning]]:
    """Validate hook commands in the given config dict.

    Returns (is_valid, warnings) where is_valid is False only when a
    critical problem is detected (e.g. empty command string).
    Warnings are issued for executables not found on PATH.
    """
    warnings: List[ValidationWarning] = []
    is_valid = True

    hooks: dict = config.get("hooks", {})
    for hook_name, commands in hooks.items():
        if not isinstance(commands, list):
            warnings.append(
                ValidationWarning(hook_name, "", "commands must be a list")
            )
            is_valid = False
            continue

        for cmd in commands:
            if not isinstance(cmd, str) or not cmd.strip():
                warnings.append(
                    ValidationWarning(hook_name, str(cmd), "command must be a non-empty string")
                )
                is_valid = False
                continue

            exe = _extract_executable(cmd)
            if exe and shutil.which(exe) is None:
                warnings.append(
                    ValidationWarning(
                        hook_name,
                        cmd,
                        f"executable '{exe}' not found on PATH",
                    )
                )

    return is_valid, warnings
