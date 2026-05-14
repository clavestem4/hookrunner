"""Git hook installer for hookrunner.

Handles installing and uninstalling hookrunner-managed hooks
into a repository's .git/hooks directory.
"""

import os
import stat
from pathlib import Path

INSTALLER_HEADER = """#!/bin/sh
# managed by hookrunner - do not edit manually
hookrunner run "$0" "$@"
"""


class InstallerError(Exception):
    """Raised when hook installation or removal fails."""


def find_git_hooks_dir(start_path: str = ".") -> Path:
    """Locate the .git/hooks directory starting from start_path.

    Walks up the directory tree until a .git directory is found.
    Raises InstallerError if no git repository is detected.
    """
    current = Path(start_path).resolve()
    while True:
        git_hooks = current / ".git" / "hooks"
        if git_hooks.is_dir():
            return git_hooks
        parent = current.parent
        if parent == current:
            raise InstallerError(
                "Not inside a git repository. Could not find .git/hooks."
            )
        current = parent


def install_hooks(hook_names: list[str], hooks_dir: Path | None = None) -> list[Path]:
    """Install hookrunner shim scripts for the given hook names.

    Returns a list of Path objects for all installed hook files.
    Raises InstallerError if a hook already exists and is not managed by hookrunner.
    """
    if hooks_dir is None:
        hooks_dir = find_git_hooks_dir()

    installed = []
    for name in hook_names:
        hook_path = hooks_dir / name
        if hook_path.exists():
            content = hook_path.read_text()
            if "managed by hookrunner" not in content:
                raise InstallerError(
                    f"Hook '{name}' already exists and is not managed by hookrunner. "
                    "Remove it manually before installing."
                )
        hook_path.write_text(INSTALLER_HEADER)
        hook_path.chmod(
            hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
        installed.append(hook_path)
    return installed


def uninstall_hooks(hook_names: list[str], hooks_dir: Path | None = None) -> list[Path]:
    """Remove hookrunner-managed hook scripts for the given hook names.

    Only removes hooks that contain the hookrunner header.
    Returns a list of Path objects for all removed hook files.
    """
    if hooks_dir is None:
        hooks_dir = find_git_hooks_dir()

    removed = []
    for name in hook_names:
        hook_path = hooks_dir / name
        if not hook_path.exists():
            continue
        content = hook_path.read_text()
        if "managed by hookrunner" in content:
            hook_path.unlink()
            removed.append(hook_path)
    return removed
