"""Core hook runner — loads config, resolves command order, and executes commands."""

from __future__ import annotations

import subprocess
from typing import List, Optional

from hookrunner.config import ConfigError, find_config_file, load_config
from hookrunner.dependency import DependencyError, resolve_command_order


class HookRunnerError(Exception):
    """Raised when hook execution fails."""


def _run_command(command: str, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run *command* in a shell and return the completed-process object."""
    return subprocess.run(
        command,
        shell=True,
        env=env,
        text=True,
        capture_output=True,
    )


def run_hook(
    hook_name: str,
    *,
    config_path: Optional[str] = None,
    env: Optional[dict] = None,
) -> List[subprocess.CompletedProcess]:
    """Execute all commands registered for *hook_name*.

    Commands are sorted according to any ``depends_on`` declarations before
    execution.  Raises :class:`HookRunnerError` on the first non-zero exit.

    Parameters
    ----------
    hook_name:
        Git hook name, e.g. ``"pre-commit"``.
    config_path:
        Explicit path to a ``.hookrunner.yml`` file.  When *None* the file is
        searched for automatically.
    env:
        Optional environment mapping forwarded to every subprocess.
    """
    if config_path is None:
        config_path = find_config_file()
    if config_path is None:
        raise HookRunnerError(
            "No .hookrunner.yml config file found in current directory or any parent."
        )

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        raise HookRunnerError(str(exc)) from exc

    hooks = config.get("hooks", {})
    hook_config = hooks.get(hook_name, {})
    commands: list = hook_config.get("commands", [])

    if not commands:
        return []

    try:
        ordered = resolve_command_order(hook_config, hook_name=hook_name)
    except DependencyError as exc:
        raise HookRunnerError(str(exc)) from exc

    results: List[subprocess.CompletedProcess] = []
    for cmd in ordered:
        run_str = cmd if isinstance(cmd, str) else cmd.get("run", "")
        if not run_str:
            continue
        result = _run_command(run_str, env=env)
        results.append(result)
        if result.returncode != 0:
            raise HookRunnerError(
                f"Command failed (exit {result.returncode}): {run_str}\n"
                f"{result.stderr.strip()}"
            )

    return results
