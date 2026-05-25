"""Template rendering for hook command strings.

Supports simple variable substitution using {VAR} syntax,
pulling values from the environment or an explicit context dict.
"""

from __future__ import annotations

import os
import re
from typing import Dict, Optional

_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class TemplateError(Exception):
    """Raised when template rendering fails."""


def render(template: str, context: Optional[Dict[str, str]] = None) -> str:
    """Render *template* by substituting ``{VAR}`` placeholders.

    Resolution order:
    1. *context* dict (if provided)
    2. Current process environment

    Raises :class:`TemplateError` if a placeholder cannot be resolved.

    >>> render("echo {MSG}", {"MSG": "hello"})
    'echo hello'
    """
    if context is None:
        context = {}

    missing: list[str] = []

    def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
        name = match.group(1)
        if name in context:
            return context[name]
        value = os.environ.get(name)
        if value is not None:
            return value
        missing.append(name)
        return match.group(0)

    result = _PLACEHOLDER_RE.sub(_replace, template)

    if missing:
        raise TemplateError(
            f"Unresolved template variable(s): {', '.join(sorted(missing))}"
        )

    return result


def render_commands(
    commands: list[str], context: Optional[Dict[str, str]] = None
) -> list[str]:
    """Render each command string in *commands*.

    Returns a new list; raises :class:`TemplateError` on the first
    unresolvable placeholder encountered.
    """
    return [render(cmd, context) for cmd in commands]


def extract_variables(template: str) -> list[str]:
    """Return the sorted list of unique variable names referenced in *template*."""
    return sorted(set(_PLACEHOLDER_RE.findall(template)))
