"""Tests for hookrunner.conditions."""

from __future__ import annotations

import pytest

from hookrunner.conditions import (
    ConditionsError,
    command_should_run,
    evaluate_condition,
)


# ---------------------------------------------------------------------------
# evaluate_condition – env_set
# ---------------------------------------------------------------------------

def test_env_set_true_when_present(monkeypatch):
    monkeypatch.setenv("MY_VAR", "hello")
    assert evaluate_condition({"env_set": "MY_VAR"}) is True


def test_env_set_false_when_missing(monkeypatch):
    monkeypatch.delenv("MY_VAR", raising=False)
    assert evaluate_condition({"env_set": "MY_VAR"}) is False


def test_env_set_false_when_empty(monkeypatch):
    monkeypatch.setenv("MY_VAR", "")
    assert evaluate_condition({"env_set": "MY_VAR"}) is False


def test_env_set_invalid_raises():
    with pytest.raises(ConditionsError, match="non-empty string"):
        evaluate_condition({"env_set": ""})


# ---------------------------------------------------------------------------
# evaluate_condition – env_equals
# ---------------------------------------------------------------------------

def test_env_equals_match(monkeypatch):
    monkeypatch.setenv("NODE_ENV", "production")
    assert evaluate_condition({"env_equals": {"var": "NODE_ENV", "value": "production"}}) is True


def test_env_equals_case_insensitive(monkeypatch):
    monkeypatch.setenv("NODE_ENV", "Production")
    assert evaluate_condition({"env_equals": {"var": "NODE_ENV", "value": "production"}}) is True


def test_env_equals_no_match(monkeypatch):
    monkeypatch.setenv("NODE_ENV", "development")
    assert evaluate_condition({"env_equals": {"var": "NODE_ENV", "value": "production"}}) is False


def test_env_equals_missing_key_raises():
    with pytest.raises(ConditionsError, match="env_equals requires"):
        evaluate_condition({"env_equals": {"var": "X"}})


# ---------------------------------------------------------------------------
# evaluate_condition – file_exists
# ---------------------------------------------------------------------------

def test_file_exists_true(tmp_path):
    f = tmp_path / "marker.txt"
    f.write_text("x")
    assert evaluate_condition({"file_exists": str(f)}) is True


def test_file_exists_false(tmp_path):
    assert evaluate_condition({"file_exists": str(tmp_path / "nope.txt")}) is False


def test_file_exists_empty_path_raises():
    with pytest.raises(ConditionsError, match="non-empty path"):
        evaluate_condition({"file_exists": ""})


# ---------------------------------------------------------------------------
# evaluate_condition – ci
# ---------------------------------------------------------------------------

def test_ci_true_when_ci_set(monkeypatch):
    monkeypatch.setenv("CI", "true")
    assert evaluate_condition({"ci": True}) is True


def test_ci_false_when_ci_not_set(monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("CONTINUOUS_INTEGRATION", raising=False)
    assert evaluate_condition({"ci": True}) is False


def test_ci_inverted(monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("CONTINUOUS_INTEGRATION", raising=False)
    assert evaluate_condition({"ci": False}) is True


# ---------------------------------------------------------------------------
# evaluate_condition – unknown key
# ---------------------------------------------------------------------------

def test_unknown_condition_raises():
    with pytest.raises(ConditionsError, match="Unknown condition type"):
        evaluate_condition({"moon_phase": "full"})


def test_empty_condition_raises():
    with pytest.raises(ConditionsError, match="Empty condition"):
        evaluate_condition({})


# ---------------------------------------------------------------------------
# command_should_run
# ---------------------------------------------------------------------------

def test_no_conditions_always_runs():
    assert command_should_run({"run": "echo hi"}) is True


def test_all_conditions_pass(monkeypatch):
    monkeypatch.setenv("FOO", "bar")
    cmd = {"run": "echo", "conditions": [{"env_set": "FOO"}]}
    assert command_should_run(cmd) is True


def test_one_condition_fails(monkeypatch):
    monkeypatch.setenv("FOO", "bar")
    monkeypatch.delenv("BAR", raising=False)
    cmd = {"run": "echo", "conditions": [{"env_set": "FOO"}, {"env_set": "BAR"}]}
    assert command_should_run(cmd) is False


def test_conditions_not_a_list_raises():
    cmd = {"run": "echo", "conditions": {"env_set": "X"}}
    with pytest.raises(ConditionsError, match="must be a list"):
        command_should_run(cmd)
