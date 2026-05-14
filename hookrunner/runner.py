"""Hook runner module: executes git hooks defined in the config."""

import os
import subprocess
import sys
from typing import Optional

from hookrunner.config import load_config, find_config_file, ConfigError


class HookRunnerError(Exception):
    """Raised when a hook execution fails."""


def run_hook(hook_name: str, config_path: Optional[str] = None) -> int:
    """
    Execute all commands defined for the given hook name.

    Returns the exit code (0 for success, non-zero for failure).
    Raises HookRunnerError if the config cannot be loaded.
    """
    if config_path is None:
        config_path = find_config_file()

    if config_path is None:
        raise HookRunnerError(
            "No .hookrunner.yml config file found in current or parent directories."
        )

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        raise HookRunnerError(f"Failed to load config: {exc}") from exc

    hooks = config.get("hooks", {})
    commands = hooks.get(hook_name, [])

    if not commands:
        # No commands defined for this hook — treat as success
        return 0

    for command in commands:
        result = _run_command(command)
        if result != 0:
            print(
                f"[hookrunner] Hook '{hook_name}' failed on command: {command}",
                file=sys.stderr,
            )
            return result

    return 0


def _run_command(command: str) -> int:
    """Run a shell command and return its exit code."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            env=os.environ.copy(),
        )
        return result.returncode
    except OSError as exc:
        print(f"[hookrunner] Error running command '{command}': {exc}", file=sys.stderr)
        return 1
