"""Tests for hookrunner.throttle."""

import time

import pytest

from hookrunner.throttle import (
    ThrottleError,
    get_last_run,
    is_throttled,
    record_run,
    reset,
)


@pytest.fixture(autouse=True)
def clear_state():
    """Ensure a clean throttle registry for every test."""
    reset()
    yield
    reset()


def test_get_last_run_returns_none_when_missing():
    assert get_last_run("pre-commit") is None


def test_record_run_stores_timestamp():
    ts = record_run("pre-commit", timestamp=100.0)
    assert ts == 100.0
    assert get_last_run("pre-commit") == 100.0


def test_record_run_uses_monotonic_when_no_timestamp(monkeypatch):
    monkeypatch.setattr(time, "monotonic", lambda: 42.5)
    ts = record_run("commit-msg")
    assert ts == 42.5


def test_record_run_raises_on_empty_name():
    with pytest.raises(ThrottleError):
        record_run("")


def test_is_throttled_false_when_no_record():
    assert is_throttled("pre-push", cooldown=5.0) is False


def test_is_throttled_true_within_cooldown(monkeypatch):
    monkeypatch.setattr(time, "monotonic", lambda: 1000.0)
    record_run("pre-commit")
    # still within cooldown window
    monkeypatch.setattr(time, "monotonic", lambda: 1002.0)
    assert is_throttled("pre-commit", cooldown=5.0) is True


def test_is_throttled_false_after_cooldown_expires(monkeypatch):
    monkeypatch.setattr(time, "monotonic", lambda: 1000.0)
    record_run("pre-commit")
    monkeypatch.setattr(time, "monotonic", lambda: 1006.0)
    assert is_throttled("pre-commit", cooldown=5.0) is False


def test_is_throttled_zero_cooldown_never_throttles(monkeypatch):
    monkeypatch.setattr(time, "monotonic", lambda: 50.0)
    record_run("pre-commit")
    assert is_throttled("pre-commit", cooldown=0) is False


def test_is_throttled_raises_on_negative_cooldown():
    with pytest.raises(ThrottleError):
        is_throttled("pre-commit", cooldown=-1)


def test_reset_specific_hook():
    record_run("pre-commit", timestamp=1.0)
    record_run("commit-msg", timestamp=2.0)
    reset("pre-commit")
    assert get_last_run("pre-commit") is None
    assert get_last_run("commit-msg") == 2.0


def test_reset_all_hooks():
    record_run("pre-commit", timestamp=1.0)
    record_run("commit-msg", timestamp=2.0)
    reset()
    assert get_last_run("pre-commit") is None
    assert get_last_run("commit-msg") is None
