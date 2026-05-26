"""Output truncation utility for hookrunner.

Truncates long command output to a configurable maximum number of lines,
optionally preserving a tail of lines so the end of output is always visible.
"""

from __future__ import annotations

from typing import List, Optional


class TruncatorError(Exception):
    """Raised when truncation configuration is invalid."""


DEFAULT_MAX_LINES = 200
DEFAULT_TAIL_LINES = 20
OMISSION_MARKER = "... [{omitted} lines omitted] ..."


def get_max_lines(config: dict, hook_name: str = "") -> Optional[int]:
    """Return the max_lines setting for *hook_name*, falling back to global."""
    hook_cfg = (config.get("hooks") or {}).get(hook_name) or {}
    value = hook_cfg.get("truncate_lines") or config.get("truncate_lines")
    if value is None:
        return None
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise TruncatorError(f"truncate_lines must be an integer, got {value!r}") from exc
    if result < 1:
        raise TruncatorError(f"truncate_lines must be >= 1, got {result}")
    return result


def get_tail_lines(config: dict, hook_name: str = "") -> int:
    """Return the tail_lines setting for *hook_name*, falling back to global."""
    hook_cfg = (config.get("hooks") or {}).get(hook_name) or {}
    value = hook_cfg.get("truncate_tail_lines") or config.get("truncate_tail_lines")
    if value is None:
        return DEFAULT_TAIL_LINES
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise TruncatorError(
            f"truncate_tail_lines must be an integer, got {value!r}"
        ) from exc
    if result < 0:
        raise TruncatorError(f"truncate_tail_lines must be >= 0, got {result}")
    return result


def truncate_lines(
    lines: List[str],
    max_lines: int,
    tail_lines: int = DEFAULT_TAIL_LINES,
    marker: str = OMISSION_MARKER,
) -> List[str]:
    """Truncate *lines* to at most *max_lines* entries.

    When truncation occurs the first ``max_lines - tail_lines`` lines are kept
    followed by an omission marker and then the final *tail_lines* lines.
    """
    if max_lines < 1:
        raise TruncatorError(f"max_lines must be >= 1, got {max_lines}")
    if tail_lines < 0:
        raise TruncatorError(f"tail_lines must be >= 0, got {tail_lines}")
    if len(lines) <= max_lines:
        return list(lines)

    effective_tail = min(tail_lines, max_lines - 1)
    head_count = max_lines - effective_tail
    head = lines[:head_count]
    tail = lines[len(lines) - effective_tail:] if effective_tail else []
    omitted = len(lines) - head_count - effective_tail
    mid = [marker.format(omitted=omitted)]
    return head + mid + tail


def truncate_text(
    text: str,
    max_lines: int,
    tail_lines: int = DEFAULT_TAIL_LINES,
    marker: str = OMISSION_MARKER,
) -> str:
    """Convenience wrapper that splits *text* on newlines, truncates, and rejoins."""
    lines = text.splitlines()
    return "\n".join(truncate_lines(lines, max_lines, tail_lines, marker))
