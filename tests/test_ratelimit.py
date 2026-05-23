"""Tests for hookrunner.ratelimit."""

from __future__ import annotations

import pytest
from pathlib import Path

from hookrunner.ratelimit import (
    RateLimitError,
    _state_path,
    is_rate_limited,
    record_run,
    reset,
    rate_limit_config_for_hook,
)


@pytest.fixture()
def base(tmp_path: Path) -> Path:
    return tmp_path / "rl"


# ---------------------------------------------------------------------------
# _state_path
# ---------------------------------------------------------------------------

def test_state_path_basic(base):
    p = _state_path("pre-commit", base)
    assert p.name == "pre-commit.json"
    assert p.parent == base


def test_state_path_sanitises_slash(base):
    p = _state_path("hooks/pre-commit", base)
    assert "/" not in p.name


def test_state_path_empty_name_raises(base):
    with pytest.raises(RateLimitError):
        _state_path("", base)


# ---------------------------------------------------------------------------
# is_rate_limited / record_run
# ---------------------------------------------------------------------------

def test_not_limited_when_no_state(base):
    assert is_rate_limited("pre-commit", max_runs=3, window_seconds=60, base=base, _now=100.0) is False


def test_not_limited_below_threshold(base):
    record_run("pre-commit", window_seconds=60, base=base, _now=100.0)
    record_run("pre-commit", window_seconds=60, base=base, _now=110.0)
    assert is_rate_limited("pre-commit", max_runs=3, window_seconds=60, base=base, _now=120.0) is False


def test_limited_at_threshold(base):
    for t in [100.0, 110.0, 120.0]:
        record_run("pre-commit", window_seconds=60, base=base, _now=t)
    assert is_rate_limited("pre-commit", max_runs=3, window_seconds=60, base=base, _now=130.0) is True


def test_old_timestamps_pruned(base):
    # Two runs far in the past — should not count in a 60 s window
    for t in [1.0, 2.0]:
        record_run("pre-commit", window_seconds=60, base=base, _now=t)
    # One recent run
    record_run("pre-commit", window_seconds=60, base=base, _now=1000.0)
    assert is_rate_limited("pre-commit", max_runs=3, window_seconds=60, base=base, _now=1010.0) is False


def test_max_runs_zero_never_limits(base):
    for _ in range(10):
        record_run("pre-commit", window_seconds=60, base=base, _now=100.0)
    assert is_rate_limited("pre-commit", max_runs=0, window_seconds=60, base=base, _now=100.0) is False


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

def test_reset_clears_state(base):
    record_run("pre-commit", window_seconds=60, base=base, _now=100.0)
    reset("pre-commit", base=base)
    assert is_rate_limited("pre-commit", max_runs=1, window_seconds=60, base=base, _now=110.0) is False


def test_reset_noop_when_no_file(base):
    reset("nonexistent", base=base)  # should not raise


# ---------------------------------------------------------------------------
# rate_limit_config_for_hook
# ---------------------------------------------------------------------------

def test_config_hook_level():
    cfg = {"hooks": {"pre-commit": {"rate_limit": {"max_runs": 5, "window_seconds": 120}}}}
    result = rate_limit_config_for_hook(cfg, "pre-commit")
    assert result == {"max_runs": 5, "window_seconds": 120.0}


def test_config_global_fallback():
    cfg = {"rate_limit": {"max_runs": 2, "window_seconds": 30}, "hooks": {}}
    result = rate_limit_config_for_hook(cfg, "pre-push")
    assert result["max_runs"] == 2


def test_config_empty_when_not_set():
    assert rate_limit_config_for_hook({}, "pre-commit") == {}


def test_config_invalid_raises():
    cfg = {"hooks": {"pre-commit": {"rate_limit": {"max_runs": "bad", "window_seconds": "also_bad"}}}}
    with pytest.raises(RateLimitError):
        rate_limit_config_for_hook(cfg, "pre-commit")
