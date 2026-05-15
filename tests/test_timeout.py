"""Tests for hookrunner.timeout."""

import time
import pytest

from hookrunner.timeout import TimeoutError, get_timeout, timeout_context


# ---------------------------------------------------------------------------
# get_timeout
# ---------------------------------------------------------------------------

def test_get_timeout_hook_specific():
    config = {"hooks": {"pre-commit": {"timeout": 30}}}
    assert get_timeout(config, "pre-commit") == 30


def test_get_timeout_global_fallback():
    config = {"settings": {"timeout": 60}, "hooks": {"pre-commit": ["echo hi"]}}
    assert get_timeout(config, "pre-commit") == 60


def test_get_timeout_hook_overrides_global():
    config = {
        "settings": {"timeout": 60},
        "hooks": {"pre-commit": {"timeout": 10}},
    }
    assert get_timeout(config, "pre-commit") == 10


def test_get_timeout_returns_none_when_not_set():
    config = {"hooks": {"pre-commit": ["echo hi"]}}
    assert get_timeout(config, "pre-commit") is None


def test_get_timeout_coerces_string_to_int():
    config = {"hooks": {"pre-commit": {"timeout": "45"}}}
    assert get_timeout(config, "pre-commit") == 45


def test_get_timeout_missing_hook():
    config = {"settings": {"timeout": 20}}
    assert get_timeout(config, "commit-msg") == 20


def test_get_timeout_empty_config():
    assert get_timeout({}, "pre-commit") is None


# ---------------------------------------------------------------------------
# TimeoutError
# ---------------------------------------------------------------------------

def test_timeout_error_message():
    err = TimeoutError("pre-commit", "pylint src/", 15)
    assert "pre-commit" in str(err)
    assert "pylint src/" in str(err)
    assert "15" in str(err)


def test_timeout_error_attributes():
    err = TimeoutError("pre-push", "npm test", 30)
    assert err.hook_name == "pre-push"
    assert err.command == "npm test"
    assert err.seconds == 30


# ---------------------------------------------------------------------------
# timeout_context
# ---------------------------------------------------------------------------

def test_timeout_context_no_op_when_zero():
    """A timeout of 0 should not interfere with execution."""
    with timeout_context(0, "pre-commit", "echo hi"):
        time.sleep(0.01)


def test_timeout_context_no_op_when_negative():
    with timeout_context(-5, "pre-commit", "echo hi"):
        pass  # should not raise


def test_timeout_context_completes_within_limit():
    with timeout_context(5, "pre-commit", "echo hi"):
        time.sleep(0.01)  # well within 5 seconds


def test_timeout_context_raises_on_exceeded():
    with pytest.raises(TimeoutError) as exc_info:
        with timeout_context(1, "pre-commit", "sleep 10"):
            time.sleep(2)
    assert exc_info.value.hook_name == "pre-commit"
    assert exc_info.value.seconds == 1
