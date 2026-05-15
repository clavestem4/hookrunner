"""hookrunner.filter — Filter hooks by branch, file pattern, or environment."""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from typing import List, Optional


class FilterError(Exception):
    """Raised when a filter cannot be evaluated."""


def current_branch() -> Optional[str]:
    """Return the current git branch name, or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def match_branch(pattern: str, branch: Optional[str] = None) -> bool:
    """Return True if *branch* matches *pattern* (glob-style)."""
    if branch is None:
        branch = current_branch()
    if branch is None:
        return False
    return fnmatch.fnmatch(branch, pattern)


def match_files(patterns: List[str], staged_files: Optional[List[str]] = None) -> bool:
    """Return True if any staged file matches any of *patterns*."""
    if staged_files is None:
        staged_files = _get_staged_files()
    for filepath in staged_files:
        for pattern in patterns:
            if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(
                os.path.basename(filepath), pattern
            ):
                return True
    return False


def _get_staged_files() -> List[str]:
    """Return list of staged file paths from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [line for line in result.stdout.splitlines() if line]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def should_run_hook(hook_config: dict, branch: Optional[str] = None,
                   staged_files: Optional[List[str]] = None) -> bool:
    """Evaluate all filters in *hook_config* and return True if the hook should run.

    Supported keys under ``filter``:
      - ``branches``: list of glob patterns; hook runs only on matching branches.
      - ``files``: list of glob patterns; hook runs only when matching files are staged.
      - ``env``: mapping of env-var name to required value (string match).
    """
    filters = hook_config.get("filter", {})
    if not filters:
        return True

    branch_patterns: List[str] = filters.get("branches", [])
    if branch_patterns:
        resolved = branch if branch is not None else current_branch()
        if not any(match_branch(p, resolved) for p in branch_patterns):
            return False

    file_patterns: List[str] = filters.get("files", [])
    if file_patterns:
        if not match_files(file_patterns, staged_files):
            return False

    env_requirements: dict = filters.get("env", {})
    for var, expected in env_requirements.items():
        actual = os.environ.get(var)
        if str(actual) != str(expected):
            return False

    return True
