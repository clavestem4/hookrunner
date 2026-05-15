"""Environment variable injection for hook commands."""

from __future__ import annotations

import os
from typing import Dict, Optional


class EnvError(Exception):
    """Raised when environment configuration is invalid."""


def load_env_block(config: dict, hook_name: str) -> Dict[str, str]:
    """Extract env vars from config for a given hook.

    Merges global ``env`` block with hook-level ``env`` block.
    Hook-level values take precedence.

    Args:
        config: Parsed hookrunner config dict.
        hook_name: Name of the hook being executed.

    Returns:
        A flat dict of environment variable names to string values.

    Raises:
        EnvError: If any value cannot be coerced to a string.
    """
    global_env: Dict[str, str] = _coerce_env(config.get("env", {}), "global")

    hooks = config.get("hooks", {})
    hook_cfg = hooks.get(hook_name, {})
    hook_env: Dict[str, str] = _coerce_env(hook_cfg.get("env", {}), hook_name)

    merged = {**global_env, **hook_env}
    return merged


def build_env(
    base: Optional[Dict[str, str]] = None,
    overrides: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Build a full environment dict by layering overrides on top of *base*.

    Args:
        base: Starting environment (defaults to ``os.environ``).
        overrides: Variables to inject / override.

    Returns:
        New dict representing the merged environment.
    """
    env = dict(base if base is not None else os.environ)
    if overrides:
        env.update(overrides)
    return env


def _coerce_env(raw: object, context: str) -> Dict[str, str]:
    """Validate and coerce a raw env mapping to ``Dict[str, str]``."""
    if not isinstance(raw, dict):
        raise EnvError(
            f"env block in '{context}' must be a mapping, got {type(raw).__name__}"
        )
    result: Dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise EnvError(f"env key {key!r} in '{context}' must be a string")
        if not isinstance(value, (str, int, float, bool)):
            raise EnvError(
                f"env value for '{key}' in '{context}' must be a scalar, "
                f"got {type(value).__name__}"
            )
        result[key] = str(value)
    return result
