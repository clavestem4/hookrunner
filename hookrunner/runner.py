"""hookrunner.runner — Execute hook commands defined in config."""

from __future__ import annotations

import subprocess
import sys
from typing import List, Optional

from hookrunner.config import ConfigError, find_config_file, load_config, validate_config
from hookrunner.filter import should_run_hook


class HookRunnerError(Exception):
    """Raised when a hook command fails or the runner encounters an error."""


def run_hook(
    hook_name: str,
    branch: Optional[str] = None,
    staged_files: Optional[List[str]] = None,
) -> int:
    """Run all commands for *hook_name*.

    Applies any ``filter`` block defined on the hook before executing commands.
    Returns the number of commands that were executed successfully.

    Raises:
        HookRunnerError: if no config file is found, config is invalid, or a
            command exits with a non-zero status.
    """
    config_path = find_config_file()
    if config_path is None:
        raise HookRunnerError(
            "No .hookrunner.yml config file found in current or parent directories."
        )

    try:
        config = load_config(config_path)
        validate_config(config)
    except ConfigError as exc:
        raise HookRunnerError(str(exc)) from exc

    hooks = config.get("hooks", {})
    hook_config = hooks.get(hook_name, {})
    commands: List[str] = hook_config.get("commands", [])

    if not commands:
        return 0

    if not should_run_hook(hook_config, branch=branch, staged_files=staged_files):
        return 0

    succeeded = 0
    for cmd in commands:
        return_code = _run_command(cmd)
        if return_code != 0:
            raise HookRunnerError(
                f"Hook '{hook_name}': command exited with code {return_code}: {cmd}"
            )
        succeeded += 1

    return succeeded


def _run_command(cmd: str) -> int:
    """Run *cmd* in a shell and return its exit code."""
    result = subprocess.run(cmd, shell=True)
    return result.returncode
