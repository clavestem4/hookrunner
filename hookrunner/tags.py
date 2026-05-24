"""Tag-based filtering for hook commands.

Allows commands within a hook to be tagged and selectively run
based on a set of active tags provided at runtime.
"""

from __future__ import annotations

from typing import Iterable


class TagsError(Exception):
    """Raised when tag configuration or filtering fails."""


def parse_tags(raw: object) -> frozenset[str]:
    """Parse a tags value from config into a frozenset of strings.

    Accepts a list of strings or a single comma-separated string.
    Raises TagsError on unexpected types.
    """
    if raw is None:
        return frozenset()
    if isinstance(raw, list):
        tags = []
        for item in raw:
            if not isinstance(item, str):
                raise TagsError(f"Tag must be a string, got {type(item).__name__}: {item!r}")
            stripped = item.strip()
            if stripped:
                tags.append(stripped)
        return frozenset(tags)
    if isinstance(raw, str):
        return frozenset(t.strip() for t in raw.split(",") if t.strip())
    raise TagsError(f"Unsupported tags value type: {type(raw).__name__}")


def command_matches_tags(
    command_tags: frozenset[str],
    active_tags: frozenset[str],
    *,
    require_all: bool = False,
) -> bool:
    """Return True if a command should run given the active tags.

    If *active_tags* is empty every command is considered a match.

    Args:
        command_tags: Tags assigned to the command in config.
        active_tags:  Tags requested by the caller (e.g. from CLI).
        require_all:  When True, the command must carry *all* active tags.
                      When False (default), any overlap is sufficient.
    """
    if not active_tags:
        return True
    if not command_tags:
        # Untagged commands are skipped when a tag filter is active.
        return False
    if require_all:
        return active_tags.issubset(command_tags)
    return bool(active_tags & command_tags)


def filter_commands(
    commands: list[dict],
    active_tags: Iterable[str],
    *,
    require_all: bool = False,
) -> list[dict]:
    """Return the subset of *commands* that match *active_tags*.

    Each command dict may optionally contain a ``"tags"`` key.  Commands
    without tags are excluded when *active_tags* is non-empty.

    Args:
        commands:    List of command dicts from the resolved config.
        active_tags: Tags to filter by; empty means return all commands.
        require_all: Forwarded to :func:`command_matches_tags`.
    """
    active = frozenset(active_tags)
    result = []
    for cmd in commands:
        if not isinstance(cmd, dict):
            raise TagsError(f"Command entry must be a dict, got {type(cmd).__name__}")
        cmd_tags = parse_tags(cmd.get("tags"))
        if command_matches_tags(cmd_tags, active, require_all=require_all):
            result.append(cmd)
    return result
