"""Output masking: replace sensitive substrings in command output."""

from __future__ import annotations

import re
from typing import Iterable, List

MASK_PLACEHOLDER = "***"


class MaskingError(Exception):
    """Raised when masking configuration or execution fails."""


def _compile_literal(value: str) -> re.Pattern:
    """Return a compiled pattern that matches *value* literally."""
    if not value:
        raise MaskingError("Mask value must be a non-empty string")
    return re.compile(re.escape(value))


def build_mask_patterns(config: dict, hook_name: str | None = None) -> List[re.Pattern]:
    """Collect mask strings from *config* and compile them into patterns.

    Sources (merged, hook-level values appended after global ones):
    - ``mask.values`` – list of literal strings to mask globally
    - ``hooks.<hook_name>.mask.values`` – hook-specific additions
    """
    raw: List[str] = []

    global_values = config.get("mask", {}).get("values", [])
    if not isinstance(global_values, list):
        raise MaskingError("'mask.values' must be a list")
    raw.extend(str(v) for v in global_values)

    if hook_name:
        hook_values = (
            config.get("hooks", {})
            .get(hook_name, {})
            .get("mask", {})
            .get("values", [])
        )
        if not isinstance(hook_values, list):
            raise MaskingError(f"'hooks.{hook_name}.mask.values' must be a list")
        raw.extend(str(v) for v in hook_values)

    patterns: List[re.Pattern] = []
    for value in raw:
        if value.strip():
            patterns.append(_compile_literal(value.strip()))
    return patterns


def mask_text(text: str, patterns: Iterable[re.Pattern]) -> str:
    """Replace every occurrence of each pattern in *text* with ``***``."""
    for pattern in patterns:
        text = pattern.sub(MASK_PLACEHOLDER, text)
    return text


def mask_env(env: dict, patterns: Iterable[re.Pattern]) -> dict:
    """Return a copy of *env* with sensitive values replaced in every entry."""
    compiled = list(patterns)
    return {key: mask_text(str(value), compiled) for key, value in env.items()}
