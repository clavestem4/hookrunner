"""Tests for hookrunner.installer module."""

import stat
from pathlib import Path

import pytest

from hookrunner.installer import (
    InstallerError,
    find_git_hooks_dir,
    install_hooks,
    uninstall_hooks,
    INSTALLER_HEADER,
)


@pytest.fixture()
def fake_git_repo(tmp_path):
    """Create a temporary directory that looks like a git repo."""
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    return tmp_path


def test_find_git_hooks_dir_finds_hooks(fake_git_repo):
    result = find_git_hooks_dir(str(fake_git_repo))
    assert result == fake_git_repo / ".git" / "hooks"


def test_find_git_hooks_dir_walks_up(fake_git_repo):
    nested = fake_git_repo / "src" / "deep"
    nested.mkdir(parents=True)
    result = find_git_hooks_dir(str(nested))
    assert result == fake_git_repo / ".git" / "hooks"


def test_find_git_hooks_dir_raises_outside_repo(tmp_path):
    with pytest.raises(InstallerError, match="Not inside a git repository"):
        find_git_hooks_dir(str(tmp_path))


def test_install_hooks_creates_executable_scripts(fake_git_repo):
    hooks_dir = fake_git_repo / ".git" / "hooks"
    installed = install_hooks(["pre-commit", "commit-msg"], hooks_dir=hooks_dir)

    assert len(installed) == 2
    for hook_path in installed:
        assert hook_path.exists()
        content = hook_path.read_text()
        assert "managed by hookrunner" in content
        assert "hookrunner run" in content
        mode = hook_path.stat().st_mode
        assert mode & stat.S_IXUSR, "Hook should be user-executable"


def test_install_hooks_overwrites_existing_managed_hook(fake_git_repo):
    hooks_dir = fake_git_repo / ".git" / "hooks"
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(INSTALLER_HEADER)

    installed = install_hooks(["pre-commit"], hooks_dir=hooks_dir)
    assert installed[0] == hook_path


def test_install_hooks_raises_on_unmanaged_existing_hook(fake_git_repo):
    hooks_dir = fake_git_repo / ".git" / "hooks"
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho 'custom hook'\n")

    with pytest.raises(InstallerError, match="not managed by hookrunner"):
        install_hooks(["pre-commit"], hooks_dir=hooks_dir)


def test_uninstall_hooks_removes_managed_hooks(fake_git_repo):
    hooks_dir = fake_git_repo / ".git" / "hooks"
    install_hooks(["pre-commit", "pre-push"], hooks_dir=hooks_dir)

    removed = uninstall_hooks(["pre-commit", "pre-push"], hooks_dir=hooks_dir)
    assert len(removed) == 2
    for hook_path in removed:
        assert not hook_path.exists()


def test_uninstall_hooks_skips_unmanaged_hooks(fake_git_repo):
    hooks_dir = fake_git_repo / ".git" / "hooks"
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho 'custom'\n")

    removed = uninstall_hooks(["pre-commit"], hooks_dir=hooks_dir)
    assert removed == []
    assert hook_path.exists()


def test_uninstall_hooks_skips_missing_hooks(fake_git_repo):
    hooks_dir = fake_git_repo / ".git" / "hooks"
    removed = uninstall_hooks(["pre-commit"], hooks_dir=hooks_dir)
    assert removed == []
