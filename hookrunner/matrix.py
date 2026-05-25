"""Matrix expansion: run hook commands across multiple variable combinations."""

from __future__ import annotations

import itertools
from typing import Any, Dict, List


class MatrixError(Exception):
    """Raised when matrix configuration is invalid."""


def parse_matrix(config: Dict[str, Any], hook_name: str) -> List[Dict[str, str]]:
    """Return a list of variable-binding dicts from the matrix block.

    Example config snippet::

        hooks:
          test:
            matrix:
              python: ["3.10", "3.11"]
              os: ["linux", "macos"]

    Returns [{'python': '3.10', 'os': 'linux'}, {'python': '3.10', 'os': 'macos'}, ...]
    """
    hooks = config.get("hooks", {})
    hook_cfg = hooks.get(hook_name, {})
    matrix_block = hook_cfg.get("matrix")

    if not matrix_block:
        return [{}]

    if not isinstance(matrix_block, dict):
        raise MatrixError(
            f"hook '{hook_name}': 'matrix' must be a mapping of variable names to lists"
        )

    for key, values in matrix_block.items():
        if not isinstance(values, list) or len(values) == 0:
            raise MatrixError(
                f"hook '{hook_name}': matrix variable '{key}' must be a non-empty list"
            )
        for v in values:
            if not isinstance(v, (str, int, float)):
                raise MatrixError(
                    f"hook '{hook_name}': matrix variable '{key}' contains non-scalar value"
                )

    keys = list(matrix_block.keys())
    value_lists = [matrix_block[k] for k in keys]
    combinations = list(itertools.product(*value_lists))
    return [dict(zip(keys, combo)) for combo in combinations]


def expand_commands(
    commands: List[str], bindings: Dict[str, str]
) -> List[str]:
    """Substitute matrix variables into each command string.

    Variables are referenced as ``{variable_name}`` inside command strings.
    Unknown placeholders are left untouched.
    """
    expanded = []
    for cmd in commands:
        try:
            expanded.append(cmd.format_map(_SafeDict(bindings)))
        except (ValueError, KeyError) as exc:  # pragma: no cover
            raise MatrixError(f"failed to expand command '{cmd}': {exc}") from exc
    return expanded


class _SafeDict(dict):
    """dict subclass that leaves unknown keys unexpanded."""

    def __missing__(self, key: str) -> str:  # type: ignore[override]
        return "{" + key + "}"
