"""Tests for hookrunner.circuit_breaker."""

import time
from pathlib import Path

import pytest

from hookrunner.circuit_breaker import (
    CircuitBreakerError,
    _state_path,
    is_open,
    record_failure,
    record_success,
    reset,
)


@pytest.fixture()
def base(tmp_path):
    return tmp_path


def test_state_path_basic(base):
    p = _state_path("pre-commit", base)
    assert p.name == "pre-commit.json"
    assert "circuit_breaker" in str(p)


def test_state_path_sanitises_separator(base):
    import os
    p = _state_path(f"hooks{os.sep}lint", base)
    assert os.sep not in p.name


def test_state_path_empty_name_raises(base):
    with pytest.raises(CircuitBreakerError):
        _state_path("", base)


def test_circuit_closed_initially(base):
    assert is_open("pre-commit", base=base) is False


def test_record_failure_increments(base):
    count = record_failure("pre-commit", threshold=3, base=base)
    assert count == 1


def test_circuit_opens_at_threshold(base):
    for _ in range(3):
        record_failure("pre-commit", threshold=3, base=base)
    assert is_open("pre-commit", threshold=3, base=base) is True


def test_circuit_stays_closed_below_threshold(base):
    for _ in range(2):
        record_failure("pre-commit", threshold=3, base=base)
    assert is_open("pre-commit", threshold=3, base=base) is False


def test_record_success_resets_circuit(base):
    for _ in range(3):
        record_failure("pre-commit", threshold=3, base=base)
    assert is_open("pre-commit", threshold=3, base=base) is True
    record_success("pre-commit", base=base)
    assert is_open("pre-commit", threshold=3, base=base) is False


def test_reset_removes_state_file(base):
    record_failure("pre-commit", threshold=1, base=base)
    from hookrunner.circuit_breaker import _state_path
    assert _state_path("pre-commit", base).exists()
    reset("pre-commit", base=base)
    assert not _state_path("pre-commit", base).exists()


def test_reset_noop_when_no_state(base):
    reset("pre-commit", base=base)  # should not raise


def test_circuit_auto_resets_after_timeout(base, monkeypatch):
    tick = [0.0]

    def fake_monotonic():
        return tick[0]

    monkeypatch.setattr(time, "monotonic", fake_monotonic)
    for _ in range(3):
        record_failure("pre-commit", threshold=3, base=base)
    assert is_open("pre-commit", threshold=3, reset_after=300, base=base) is True
    tick[0] = 301.0
    assert is_open("pre-commit", threshold=3, reset_after=300, base=base) is False


def test_corrupt_state_raises(base):
    from hookrunner.circuit_breaker import CIRCUIT_BREAKER_DIR
    p = base / CIRCUIT_BREAKER_DIR / "bad-hook.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{not valid json")
    with pytest.raises(CircuitBreakerError):
        is_open("bad-hook", base=base)
