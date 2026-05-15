"""Redact sensitive environment variables from logs and output."""

import re
from typing import Dict, List, Optional

REDACTED = "***REDACTED***"

_DEFAULT_PATTERNS = [
    re.compile(r"(?i)(password|passwd|secret|token|api_key|apikey|auth|credential|private_key)"),
]


class RedactorError(Exception):
    """Raised when redactor configuration is invalid."""


def _compile_patterns(extra_patterns: Optional[List[str]] = None) -> List[re.Pattern]:
    """Combine default patterns with any user-supplied regex strings."""
    patterns = list(_DEFAULT_PATTERNS)
    if extra_patterns:
        for raw in extra_patterns:
            try:
                patterns.append(re.compile(raw))
            except re.error as exc:
                raise RedactorError(f"Invalid redact pattern {raw!r}: {exc}") from exc
    return patterns


def build_redact_set(
    env: Dict[str, str],
    extra_patterns: Optional[List[str]] = None,
) -> frozenset:
    """Return the set of env var *names* whose values should be redacted."""
    patterns = _compile_patterns(extra_patterns)
    sensitive: set = set()
    for key in env:
        if any(p.search(key) for p in patterns):
            sensitive.add(key)
    return frozenset(sensitive)


def redact_env(
    env: Dict[str, str],
    extra_patterns: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Return a copy of *env* with sensitive values replaced by REDACTED."""
    sensitive = build_redact_set(env, extra_patterns)
    return {k: (REDACTED if k in sensitive else v) for k, v in env.items()}


def redact_string(
    text: str,
    env: Dict[str, str],
    extra_patterns: Optional[List[str]] = None,
) -> str:
    """Replace occurrences of sensitive env values inside *text*."""
    sensitive = build_redact_set(env, extra_patterns)
    result = text
    for key in sensitive:
        value = env.get(key, "")
        if value:
            result = result.replace(value, REDACTED)
    return result
