"""Tests for hookrunner.debounce."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from hookrunner.debounce import (
    DebounceError,
    get_last_fired,
    get_window,
    is_debounced,
    record_fired,
    reset,
)


@pytest.fixture()
def base(tmp_path: Path) -> Path:
    return tmp_path / "debounce"


def test_get_last_fired_returns_none_when_missing(base):
    assert get_last_fired("pre-commit", base) is None


def test_record_and_get_last_fired(base):
    ts = time.time()
    record_fired("pre-commit", base, timestamp=ts)
    result = get_last_fired("pre-commit", base)
    assert result == pytest.approx(ts)


def test_record_creates_parent_dirs(tmp_path):
    deep = tmp_path / "a" / "b" / "c"
    record_fired("pre-push", deep)
    assert get_last_fired("pre-push", deep) is not None


def test_record_raises_on_empty_name(base):
    with pytest.raises(DebounceError, match="must not be empty"):
        record_fired("", base)


def test_get_last_fired_raises_on_corrupt_file(base):
    base.mkdir(parents=True, exist_ok=True)
    state_file = base / "pre-commit.debounce.json"
    state_file.write_text("not-json")
    with pytest.raises(DebounceError):
        get_last_fired("pre-commit", base)


def test_is_debounced_true_within_window(base):
    record_fired("pre-commit", base, timestamp=time.time())
    assert is_debounced("pre-commit", window=60.0, base=base) is True


def test_is_debounced_false_after_window(base):
    record_fired("pre-commit", base, timestamp=time.time() - 120.0)
    assert is_debounced("pre-commit", window=5.0, base=base) is False


def test_is_debounced_false_when_no_state(base):
    assert is_debounced("pre-commit", window=10.0, base=base) is False


def test_reset_removes_state(base):
    record_fired("pre-commit", base, timestamp=time.time())
    reset("pre-commit", base)
    assert get_last_fired("pre-commit", base) is None


def test_reset_noop_when_missing(base):
    reset("pre-commit", base)  # should not raise


def test_get_window_hook_level(base):
    config = {"hooks": {"pre-commit": {"debounce": 5}}}
    assert get_window(config, "pre-commit") == 5.0


def test_get_window_global_dict(base):
    config = {"debounce": {"window": 3}}
    assert get_window(config, "pre-commit") == 3.0


def test_get_window_global_scalar(base):
    config = {"debounce": 7}
    assert get_window(config, "pre-commit") == 7.0


def test_get_window_default_when_absent(base):
    from hookrunner.debounce import DEFAULT_WINDOW
    assert get_window({}, "pre-commit") == DEFAULT_WINDOW


def test_hook_level_overrides_global(base):
    config = {"debounce": {"window": 30}, "hooks": {"pre-commit": {"debounce": 1}}}
    assert get_window(config, "pre-commit") == 1.0
