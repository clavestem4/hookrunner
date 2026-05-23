"""Tests for hookrunner.lockfile."""

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from hookrunner.lockfile import (
    LockfileError,
    _lock_path,
    acquire,
    is_locked,
    release,
)


@pytest.fixture()
def lock_dir(tmp_path):
    return tmp_path / "locks"


# ---------------------------------------------------------------------------
# _lock_path
# ---------------------------------------------------------------------------

def test_lock_path_basic(lock_dir):
    p = _lock_path("pre-commit", lock_dir)
    assert p == lock_dir / "pre-commit.lock"


def test_lock_path_empty_name_raises(lock_dir):
    with pytest.raises(LockfileError, match="non-empty"):
        _lock_path("", lock_dir)


def test_lock_path_sanitises_separator(lock_dir):
    p = _lock_path("hooks/pre-commit", lock_dir)
    assert os.sep not in p.name


# ---------------------------------------------------------------------------
# acquire / release
# ---------------------------------------------------------------------------

def test_acquire_creates_lock_file(lock_dir):
    pid = acquire("pre-commit", lock_dir)
    path = _lock_path("pre-commit", lock_dir)
    assert path.exists()
    assert int(path.read_text()) == pid == os.getpid()
    release("pre-commit", lock_dir)


def test_release_removes_lock_file(lock_dir):
    acquire("pre-push", lock_dir)
    release("pre-push", lock_dir)
    assert not _lock_path("pre-push", lock_dir).exists()


def test_release_raises_when_no_lock(lock_dir):
    with pytest.raises(LockfileError, match="No lock file"):
        release("commit-msg", lock_dir)


def test_release_raises_when_owned_by_other_pid(lock_dir):
    path = _lock_path("pre-commit", lock_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(os.getpid() + 9999))
    with pytest.raises(LockfileError, match="owned by PID"):
        release("pre-commit", lock_dir)
    path.unlink()


def test_release_raises_on_corrupt_lock_file(lock_dir):
    path = _lock_path("pre-commit", lock_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-a-pid")
    with pytest.raises(LockfileError, match="Corrupt"):
        release("pre-commit", lock_dir)
    path.unlink()


# ---------------------------------------------------------------------------
# is_locked
# ---------------------------------------------------------------------------

def test_is_locked_true_when_acquired(lock_dir):
    acquire("pre-commit", lock_dir)
    assert is_locked("pre-commit", lock_dir) is True
    release("pre-commit", lock_dir)


def test_is_locked_false_when_no_file(lock_dir):
    assert is_locked("pre-commit", lock_dir) is False


def test_is_locked_false_for_stale_lock(lock_dir):
    path = _lock_path("pre-commit", lock_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write a PID that almost certainly does not exist
    path.write_text("999999")
    assert is_locked("pre-commit", lock_dir) is False


# ---------------------------------------------------------------------------
# timeout
# ---------------------------------------------------------------------------

def test_acquire_times_out_when_lock_held(lock_dir):
    acquire("pre-commit", lock_dir)
    try:
        with patch("hookrunner.lockfile.os.getpid", return_value=os.getpid() + 1):
            with pytest.raises(LockfileError, match="Could not acquire"):
                acquire("pre-commit", lock_dir, timeout=0)
    finally:
        _lock_path("pre-commit", lock_dir).unlink(missing_ok=True)
