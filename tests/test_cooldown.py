"""Tests for hookrunner.cooldown."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from hookrunner.cooldown import (
    CooldownError,
    _state_path,
    cooldown_period_for_hook,
    get_last_run,
    is_cooling_down,
    record_run,
    reset,
)


@pytest.fixture()
def base(tmp_path: Path) -> Path:
    return tmp_path / "cooldown"


def test_state_path_basic(base: Path) -> None:
    p = _state_path("pre-commit", base)
    assert p == base / "pre-commit.json"


def test_state_path_sanitises_separator(base: Path) -> None:
    p = _state_path("hooks/pre-commit", base)
    assert "/" not in p.name


def test_state_path_empty_name_raises(base: Path) -> None:
    with pytest.raises(CooldownError):
        _state_path("", base)


def test_get_last_run_returns_none_when_missing(base: Path) -> None:
    assert get_last_run("pre-commit", base) is None


def test_record_and_get_last_run(base: Path) -> None:
    record_run("pre-commit", base, timestamp=1000.0)
    assert get_last_run("pre-commit", base) == pytest.approx(1000.0)


def test_record_creates_parent_dirs(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b" / "c"
    record_run("hook", deep, timestamp=42.0)
    assert get_last_run("hook", deep) == pytest.approx(42.0)


def test_record_raises_on_empty_name(base: Path) -> None:
    with pytest.raises(CooldownError):
        record_run("", base)


def test_get_last_run_raises_on_corrupt_file(base: Path) -> None:
    p = _state_path("bad", base)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{not valid json")
    with pytest.raises(CooldownError):
        get_last_run("bad", base)


def test_is_cooling_down_false_when_no_state(base: Path) -> None:
    assert is_cooling_down("pre-commit", 60.0, base) is False


def test_is_cooling_down_true_within_period(base: Path) -> None:
    now = time.monotonic()
    record_run("pre-commit", base, timestamp=now)
    assert is_cooling_down("pre-commit", 60.0, base) is True


def test_is_cooling_down_false_after_period_elapsed(base: Path) -> None:
    old = time.monotonic() - 120.0
    record_run("pre-commit", base, timestamp=old)
    assert is_cooling_down("pre-commit", 60.0, base) is False


def test_is_cooling_down_zero_period_never_throttles(base: Path) -> None:
    record_run("pre-commit", base, timestamp=time.monotonic())
    assert is_cooling_down("pre-commit", 0, base) is False


def test_cooldown_period_hook_specific() -> None:
    config = {"hooks": {"pre-commit": {"cooldown": 30}}}
    assert cooldown_period_for_hook("pre-commit", config) == 30.0


def test_cooldown_period_global_fallback() -> None:
    config = {"settings": {"cooldown_period": 15}}
    assert cooldown_period_for_hook("pre-commit", config) == 15.0


def test_cooldown_period_hook_overrides_global() -> None:
    config = {"hooks": {"pre-commit": {"cooldown": 5}}, "settings": {"cooldown_period": 60}}
    assert cooldown_period_for_hook("pre-commit", config) == 5.0


def test_cooldown_period_returns_zero_when_not_set() -> None:
    assert cooldown_period_for_hook("pre-commit", {}) == 0.0


def test_reset_removes_state(base: Path) -> None:
    record_run("pre-commit", base, timestamp=999.0)
    reset("pre-commit", base)
    assert get_last_run("pre-commit", base) is None


def test_reset_noop_when_missing(base: Path) -> None:
    reset("nonexistent", base)  # should not raise
