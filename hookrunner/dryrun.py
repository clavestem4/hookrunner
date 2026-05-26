"""Dry-run support: simulate hook execution without running commands."""

from __future__ import annotations

from typing import List, Dict, Any


class DryRunError(Exception):
    """Raised when dry-run configuration is invalid."""


def is_dry_run(config: Dict[str, Any], hook_name: str) -> bool:
    """Return True if dry-run mode is enabled for the given hook.

    Precedence: hook-level > global.  A missing key is treated as False.
    """
    if not isinstance(config, dict):
        raise DryRunError("config must be a dict")
    if not hook_name or not hook_name.strip():
        raise DryRunError("hook_name must be a non-empty string")

    hooks = config.get("hooks", {})
    hook_cfg = hooks.get(hook_name, {}) if isinstance(hooks, dict) else {}

    # Hook-level setting takes precedence.
    if "dry_run" in hook_cfg:
        value = hook_cfg["dry_run"]
        if not isinstance(value, bool):
            raise DryRunError(
                f"hooks.{hook_name}.dry_run must be a boolean, got {type(value).__name__!r}"
            )
        return value

    # Fall back to global setting.
    global_value = config.get("dry_run", False)
    if not isinstance(global_value, bool):
        raise DryRunError(
            f"global dry_run must be a boolean, got {type(global_value).__name__!r}"
        )
    return global_value


def simulate_hook(hook_name: str, commands: List[str]) -> List[Dict[str, Any]]:
    """Return a list of simulated result records without executing anything.

    Each record mirrors the shape produced by runner.run_hook so callers can
    display output consistently.
    """
    if not hook_name or not hook_name.strip():
        raise DryRunError("hook_name must be a non-empty string")
    if not isinstance(commands, list):
        raise DryRunError("commands must be a list")

    results = []
    for cmd in commands:
        if not isinstance(cmd, str):
            raise DryRunError(f"each command must be a string, got {type(cmd).__name__!r}")
        results.append(
            {
                "hook": hook_name,
                "command": cmd,
                "dry_run": True,
                "returncode": 0,
                "stdout": "",
                "stderr": "",
            }
        )
    return results


def format_dry_run_output(results: List[Dict[str, Any]]) -> str:
    """Return a human-readable summary of simulated commands."""
    if not results:
        return "(dry-run) No commands to simulate."

    lines = []
    hook = results[0].get("hook", "unknown")
    lines.append(f"(dry-run) Hook: {hook}")
    for i, r in enumerate(results, start=1):
        lines.append(f"  [{i}] {r.get('command', '')}  -> would run (skipped)")
    return "\n".join(lines)
