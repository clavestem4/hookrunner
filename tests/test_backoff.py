"""Tests for hookrunner.backoff."""

from __future__ import annotations

import pytest

from hookrunner.backoff import (
    BackoffError,
    backoff_config_for_hook,
    compute_delay,
    sleep_with_backoff,
)


# ---------------------------------------------------------------------------
# compute_delay
# ---------------------------------------------------------------------------

def test_compute_delay_no_jitter_attempt_0():
    delay = compute_delay(0, base=1.0, factor=2.0, max_delay=60.0, jitter=False)
    assert delay == pytest.approx(1.0)


def test_compute_delay_no_jitter_grows_exponentially():
    delays = [compute_delay(i, base=1.0, factor=2.0, max_delay=100.0, jitter=False)
              for i in range(5)]
    assert delays == pytest.approx([1.0, 2.0, 4.0, 8.0, 16.0])


def test_compute_delay_capped_by_max_delay():
    delay = compute_delay(20, base=1.0, factor=2.0, max_delay=30.0, jitter=False)
    assert delay == pytest.approx(30.0)


def test_compute_delay_jitter_within_bounds():
    for _ in range(50):
        delay = compute_delay(3, base=1.0, factor=2.0, max_delay=60.0, jitter=True)
        assert 0.0 <= delay < 8.0  # base * factor^3 = 8.0


def test_compute_delay_raises_on_negative_attempt():
    with pytest.raises(BackoffError, match="attempt"):
        compute_delay(-1)


def test_compute_delay_raises_on_zero_base():
    with pytest.raises(BackoffError, match="base"):
        compute_delay(0, base=0)


def test_compute_delay_raises_on_factor_less_than_one():
    with pytest.raises(BackoffError, match="factor"):
        compute_delay(0, factor=0.5)


def test_compute_delay_raises_on_zero_max_delay():
    with pytest.raises(BackoffError, match="max_delay"):
        compute_delay(0, max_delay=0)


# ---------------------------------------------------------------------------
# backoff_config_for_hook
# ---------------------------------------------------------------------------

def test_backoff_config_defaults_when_no_config():
    cfg = backoff_config_for_hook({}, "pre-commit")
    assert cfg == {"base": 1.0, "factor": 2.0, "max_delay": 60.0, "jitter": True}


def test_backoff_config_global_overrides_defaults():
    config = {"backoff": {"base": 0.5, "max_delay": 10.0}}
    cfg = backoff_config_for_hook(config, "pre-commit")
    assert cfg["base"] == pytest.approx(0.5)
    assert cfg["max_delay"] == pytest.approx(10.0)
    assert cfg["factor"] == pytest.approx(2.0)  # still default


def test_backoff_config_hook_overrides_global():
    config = {
        "backoff": {"base": 2.0, "factor": 3.0},
        "hooks": {
            "pre-push": {"backoff": {"base": 0.1}}
        },
    }
    cfg = backoff_config_for_hook(config, "pre-push")
    assert cfg["base"] == pytest.approx(0.1)
    assert cfg["factor"] == pytest.approx(3.0)  # from global


def test_backoff_config_coerces_strings_to_float():
    config = {"backoff": {"base": "2", "factor": "4", "max_delay": "120"}}
    cfg = backoff_config_for_hook(config, "pre-commit")
    assert isinstance(cfg["base"], float)
    assert isinstance(cfg["factor"], float)


# ---------------------------------------------------------------------------
# sleep_with_backoff
# ---------------------------------------------------------------------------

def test_sleep_with_backoff_calls_sleep_with_computed_delay():
    slept: list[float] = []
    returned = sleep_with_backoff(
        attempt=2,
        base=1.0,
        factor=2.0,
        max_delay=60.0,
        jitter=False,
        _sleep=slept.append,
    )
    assert slept == [pytest.approx(4.0)]
    assert returned == pytest.approx(4.0)


def test_sleep_with_backoff_returns_actual_delay():
    delays: list[float] = []
    result = sleep_with_backoff(0, base=5.0, jitter=False, _sleep=delays.append)
    assert result == pytest.approx(5.0)
