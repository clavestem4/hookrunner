"""Tests for hookrunner.semaphore."""

import os
import pytest
from unittest.mock import patch

from hookrunner.semaphore import (
    acquire,
    release,
    current_count,
    reset,
    SemaphoreError,
    _semaphore_path,
)

HOOK_NAME = "pre-commit-test"


@pytest.fixture(autouse=True)
def clean_semaphore():
    reset(HOOK_NAME)
    yield
    reset(HOOK_NAME)


def test_acquire_returns_pid():
    slot = acquire(HOOK_NAME)
    assert slot == os.getpid()


def test_acquire_increments_count():
    acquire(HOOK_NAME)
    assert current_count(HOOK_NAME) == 1


def test_release_decrements_count():
    slot = acquire(HOOK_NAME)
    release(HOOK_NAME, slot)
    assert current_count(HOOK_NAME) == 0


def test_release_unknown_slot_raises():
    with pytest.raises(SemaphoreError, match="already released"):
        release(HOOK_NAME, 99999)


def test_current_count_zero_when_no_slots():
    assert current_count(HOOK_NAME) == 0


def test_acquire_respects_max_workers():
    """Filling all slots then acquiring with timeout=0 must raise."""
    pid = os.getpid()
    # Manually stuff the state with fake-but-alive PIDs (use current pid repeated)
    from hookrunner.semaphore import _write_state, _semaphore_path
    path = _semaphore_path(HOOK_NAME)
    _write_state(path, {"slots": [pid, pid, pid]})

    with pytest.raises(SemaphoreError, match="max_workers=3"):
        acquire(HOOK_NAME, max_workers=3, timeout=0)


def test_acquire_evicts_dead_pids():
    """Dead PIDs should be evicted so a slot becomes available."""
    from hookrunner.semaphore import _write_state, _semaphore_path
    path = _semaphore_path(HOOK_NAME)
    _write_state(path, {"slots": [999999999]})  # almost certainly dead

    slot = acquire(HOOK_NAME, max_workers=1, timeout=0)
    assert slot == os.getpid()


def test_reset_clears_all_slots():
    acquire(HOOK_NAME)
    reset(HOOK_NAME)
    assert current_count(HOOK_NAME) == 0


def test_semaphore_path_sanitises_slashes():
    path = _semaphore_path("hooks/pre-commit")
    assert "/" not in path.name or path.name.startswith("hooks")
    assert "hooks_pre-commit" in path.name


def test_multiple_slots_within_limit():
    pid = os.getpid()
    slot1 = acquire(HOOK_NAME, max_workers=3)
    # Simulate a second "process" by patching getpid
    with patch("os.getpid", return_value=pid + 1):
        slot2 = acquire(HOOK_NAME, max_workers=3)
    assert current_count(HOOK_NAME) == 2
    release(HOOK_NAME, slot1)
    release(HOOK_NAME, slot2)
    assert current_count(HOOK_NAME) == 0
