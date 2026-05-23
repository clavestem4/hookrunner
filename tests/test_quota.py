"""Tests for hookrunner.quota."""

from __future__ import annotations

import pytest
from pathlib import Path

from hookrunner.quota import (
    QuotaError,
    _state_path,
    _load_timestamps,
    is_quota_exceeded,
    record_execution,
    reset_quota,
    quota_config_for_hook,
)


@pytest.fixture()
def base(tmp_path: Path) -> Path:
    return tmp_path / "quota"


# ---------------------------------------------------------------------------
# _state_path
# ---------------------------------------------------------------------------

def test_state_path_basic(base: Path) -> None:
    p = _state_path("pre-commit", base)
    assert p == base / "pre-commit.quota.json"


def test_state_path_sanitises_separator(base: Path) -> None:
    p = _state_path("hooks/pre-commit", base)
    assert "/" not in p.name


def test_state_path_empty_name_raises(base: Path) -> None:
    with pytest.raises(QuotaError, match="empty"):
        _state_path("", base)


# ---------------------------------------------------------------------------
# is_quota_exceeded
# ---------------------------------------------------------------------------

def test_not_exceeded_when_no_state(base: Path) -> None:
    assert is_quota_exceeded("pre-commit", limit=3, window=60, base=base) is False


def test_not_exceeded_below_limit(base: Path) -> None:
    now = 1000.0
    for i in range(2):
        record_execution("pre-commit", base=base, _now=now + i)
    assert is_quota_exceeded("pre-commit", limit=3, window=60, base=base, _now=now + 5) is False


def test_exceeded_at_limit(base: Path) -> None:
    now = 1000.0
    for i in range(3):
        record_execution("pre-commit", base=base, _now=now + i)
    assert is_quota_exceeded("pre-commit", limit=3, window=60, base=base, _now=now + 5) is True


def test_old_timestamps_excluded_from_window(base: Path) -> None:
    now = 1000.0
    # Record 3 executions well outside the window
    for i in range(3):
        record_execution("pre-commit", base=base, _now=now + i)
    # Check far in the future so those timestamps fall outside the 60-second window
    future = now + 120
    assert is_quota_exceeded("pre-commit", limit=3, window=60, base=base, _now=future) is False


def test_invalid_limit_raises(base: Path) -> None:
    with pytest.raises(QuotaError, match="limit"):
        is_quota_exceeded("pre-commit", limit=0, window=60, base=base)


def test_invalid_window_raises(base: Path) -> None:
    with pytest.raises(QuotaError, match="window"):
        is_quota_exceeded("pre-commit", limit=3, window=0, base=base)


# ---------------------------------------------------------------------------
# record_execution
# ---------------------------------------------------------------------------

def test_record_creates_state_file(base: Path) -> None:
    record_execution("pre-commit", base=base, _now=500.0)
    path = base / "pre-commit.quota.json"
    assert path.exists()


def test_record_appends_timestamps(base: Path) -> None:
    for i in range(4):
        record_execution("pre-commit", base=base, _now=float(i))
    timestamps = _load_timestamps(base / "pre-commit.quota.json")
    assert len(timestamps) == 4


def test_record_raises_on_empty_name(base: Path) -> None:
    with pytest.raises(QuotaError, match="empty"):
        record_execution("", base=base)


# ---------------------------------------------------------------------------
# reset_quota
# ---------------------------------------------------------------------------

def test_reset_removes_state_file(base: Path) -> None:
    record_execution("pre-commit", base=base, _now=1.0)
    reset_quota("pre-commit", base=base)
    assert not (base / "pre-commit.quota.json").exists()


def test_reset_noop_when_no_state(base: Path) -> None:
    reset_quota("pre-commit", base=base)  # should not raise


# ---------------------------------------------------------------------------
# quota_config_for_hook
# ---------------------------------------------------------------------------

def test_quota_config_global_only() -> None:
    config = {"quota": {"limit": 5, "window": 3600}}
    result = quota_config_for_hook(config, "pre-commit")
    assert result == {"limit": 5, "window": 3600}


def test_quota_config_hook_overrides_global() -> None:
    config = {
        "quota": {"limit": 5, "window": 3600},
        "hooks": {"pre-commit": {"quota": {"limit": 2}}},
    }
    result = quota_config_for_hook(config, "pre-commit")
    assert result["limit"] == 2
    assert result["window"] == 3600


def test_quota_config_empty_when_not_set() -> None:
    config: dict = {}
    result = quota_config_for_hook(config, "pre-commit")
    assert result == {}
