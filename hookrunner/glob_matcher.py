"""Glob-based file pattern matching for hook command filtering."""

from __future__ import annotations

import fnmatch
import os
from typing import Iterable, List, Optional, Sequence


class GlobMatcherError(Exception):
    """Raised when glob pattern configuration is invalid."""


def parse_patterns(raw: object) -> List[str]:
    """Return a list of glob patterns from a config value.

    Accepts a list of strings or a single whitespace-separated string.
    Raises GlobMatcherError if the value is not a recognised type.
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        patterns = [str(p).strip() for p in raw]
        return [p for p in patterns if p]
    if isinstance(raw, str):
        return [p for p in raw.split() if p]
    raise GlobMatcherError(
        f"'patterns' must be a list or whitespace-separated string, got {type(raw).__name__!r}"
    )


def match_any(path: str, patterns: Sequence[str]) -> bool:
    """Return True if *path* matches at least one glob *pattern*.

    Matching is performed against the basename **and** the full path so that
    both ``*.py`` and ``src/*.py`` work as expected.
    """
    normalised = path.replace(os.sep, "/")
    basename = os.path.basename(normalised)
    for pattern in patterns:
        if fnmatch.fnmatch(basename, pattern):
            return True
        if fnmatch.fnmatch(normalised, pattern):
            return True
    return False


def filter_paths(
    paths: Iterable[str],
    include: Optional[Sequence[str]] = None,
    exclude: Optional[Sequence[str]] = None,
) -> List[str]:
    """Filter *paths* using optional *include* and *exclude* glob lists.

    - If *include* is non-empty a path must match at least one pattern.
    - If *exclude* is non-empty a path must **not** match any pattern.
    - Both filters are applied when both are provided.
    """
    result: List[str] = []
    for path in paths:
        if include and not match_any(path, include):
            continue
        if exclude and match_any(path, exclude):
            continue
        result.append(path)
    return result


def command_matches_globs(command: dict, paths: Sequence[str]) -> bool:
    """Return True if *command* should run given the changed *paths*.

    Reads optional ``include_patterns`` and ``exclude_patterns`` keys from
    *command*.  If neither key is present the command always matches.
    """
    raw_include = command.get("include_patterns")
    raw_exclude = command.get("exclude_patterns")

    include = parse_patterns(raw_include)
    exclude = parse_patterns(raw_exclude)

    if not include and not exclude:
        return True

    matched = filter_paths(paths, include=include or None, exclude=exclude or None)
    return bool(matched)
