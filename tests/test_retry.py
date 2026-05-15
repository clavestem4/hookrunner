"""Tests for hookrunner.retry."""

import pytest

from hookrunner.retry import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_DELAY_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    RetryError,
    retry,
    retry_config_for_hook,
)


# ---------------------------------------------------------------------------
# retry()
# ---------------------------------------------------------------------------

def test_retry_succeeds_on_first_attempt():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    result = retry(fn, max_attempts=3, delay=0)
    assert result == "ok"
    assert len(calls) == 1


def test_retry_succeeds_after_failures(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    attempts = []

    def fn():
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("transient")
        return "done"

    result = retry(fn, max_attempts=5, delay=0.01)
    assert result == "done"
    assert len(attempts) == 3


def test_retry_raises_after_all_attempts(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)

    def fn():
        raise ValueError("always fails")

    with pytest.raises(RetryError, match="3 attempt"):
        retry(fn, max_attempts=3, delay=0.01, exceptions=(ValueError,))


def test_retry_does_not_catch_unlisted_exception(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)

    def fn():
        raise KeyError("unexpected")

    with pytest.raises(KeyError):
        retry(fn, max_attempts=3, delay=0, exceptions=(ValueError,))


def test_retry_calls_on_retry_callback(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    seen = []

    def fn():
        raise OSError("boom")

    def on_retry(attempt, exc):
        seen.append((attempt, str(exc)))

    with pytest.raises(RetryError):
        retry(fn, max_attempts=3, delay=0, on_retry=on_retry)

    assert seen == [(1, "boom"), (2, "boom")]


def test_retry_raises_on_invalid_max_attempts():
    with pytest.raises(ValueError, match="max_attempts"):
        retry(lambda: None, max_attempts=0)


def test_retry_applies_backoff(monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", lambda s: slept.append(s))

    def fn():
        raise RuntimeError("fail")

    with pytest.raises(RetryError):
        retry(fn, max_attempts=3, delay=1.0, backoff=2.0)

    assert slept == [1.0, 2.0]


# ---------------------------------------------------------------------------
# retry_config_for_hook()
# ---------------------------------------------------------------------------

def test_retry_config_defaults_when_empty():
    cfg = retry_config_for_hook({})
    assert cfg["max_attempts"] == DEFAULT_MAX_ATTEMPTS
    assert cfg["delay"] == DEFAULT_DELAY_SECONDS
    assert cfg["backoff"] == DEFAULT_BACKOFF_FACTOR


def test_retry_config_reads_hook_values():
    cfg = retry_config_for_hook(
        {"retry_attempts": 5, "retry_delay": 0.5, "retry_backoff": 1.5}
    )
    assert cfg == {"max_attempts": 5, "delay": 0.5, "backoff": 1.5}


def test_retry_config_coerces_types():
    cfg = retry_config_for_hook(
        {"retry_attempts": "2", "retry_delay": "0.25", "retry_backoff": "3"}
    )
    assert isinstance(cfg["max_attempts"], int)
    assert isinstance(cfg["delay"], float)
    assert isinstance(cfg["backoff"], float)
