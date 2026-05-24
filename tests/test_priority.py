"""Tests for hookrunner.priority."""

import pytest

from hookrunner.priority import (
    DEFAULT_PRIORITY,
    PriorityError,
    filter_by_min_priority,
    get_priority,
    priority_config_for_hook,
    sort_commands,
)


# ---------------------------------------------------------------------------
# get_priority
# ---------------------------------------------------------------------------

def test_get_priority_default_when_missing():
    assert get_priority({}) == DEFAULT_PRIORITY


def test_get_priority_explicit_value():
    assert get_priority({"priority": 80}) == 80


def test_get_priority_string_coerced():
    assert get_priority({"priority": "30"}) == 30


def test_get_priority_zero_allowed():
    assert get_priority({"priority": 0}) == 0


def test_get_priority_max_allowed():
    assert get_priority({"priority": 100}) == 100


def test_get_priority_non_integer_raises():
    with pytest.raises(PriorityError, match="integer"):
        get_priority({"priority": "high"})


def test_get_priority_above_max_raises():
    with pytest.raises(PriorityError, match="between"):
        get_priority({"priority": 101})


def test_get_priority_below_min_raises():
    with pytest.raises(PriorityError, match="between"):
        get_priority({"priority": -1})


# ---------------------------------------------------------------------------
# sort_commands
# ---------------------------------------------------------------------------

def test_sort_commands_highest_first_by_default():
    cmds = [
        {"run": "a", "priority": 10},
        {"run": "b", "priority": 90},
        {"run": "c", "priority": 50},
    ]
    result = sort_commands(cmds)
    assert [c["run"] for c in result] == ["b", "c", "a"]


def test_sort_commands_lowest_first_when_reversed():
    cmds = [
        {"run": "a", "priority": 10},
        {"run": "b", "priority": 90},
    ]
    result = sort_commands(cmds, reverse=False)
    assert result[0]["run"] == "a"


def test_sort_commands_stable_on_equal_priority():
    cmds = [
        {"run": "first", "priority": 50},
        {"run": "second", "priority": 50},
    ]
    result = sort_commands(cmds)
    assert [c["run"] for c in result] == ["first", "second"]


def test_sort_commands_uses_default_priority():
    cmds = [{"run": "a"}, {"run": "b", "priority": 80}]
    result = sort_commands(cmds)
    assert result[0]["run"] == "b"


# ---------------------------------------------------------------------------
# filter_by_min_priority
# ---------------------------------------------------------------------------

def test_filter_keeps_commands_at_or_above_threshold():
    cmds = [
        {"run": "low", "priority": 20},
        {"run": "mid", "priority": 50},
        {"run": "high", "priority": 80},
    ]
    result = filter_by_min_priority(cmds, 50)
    assert {c["run"] for c in result} == {"mid", "high"}


def test_filter_returns_empty_when_none_qualify():
    cmds = [{"run": "low", "priority": 10}]
    assert filter_by_min_priority(cmds, 90) == []


def test_filter_invalid_threshold_raises():
    with pytest.raises(PriorityError):
        filter_by_min_priority([], 150)


# ---------------------------------------------------------------------------
# priority_config_for_hook
# ---------------------------------------------------------------------------

def test_priority_config_hook_specific():
    cfg = {"hooks": {"pre-commit": {"min_priority": 40}}}
    assert priority_config_for_hook(cfg, "pre-commit") == 40


def test_priority_config_global_fallback():
    cfg = {"min_priority": 25, "hooks": {}}
    assert priority_config_for_hook(cfg, "pre-push") == 25


def test_priority_config_hook_overrides_global():
    cfg = {"min_priority": 25, "hooks": {"pre-commit": {"min_priority": 70}}}
    assert priority_config_for_hook(cfg, "pre-commit") == 70


def test_priority_config_returns_none_when_not_set():
    assert priority_config_for_hook({}, "pre-commit") is None


def test_priority_config_invalid_value_raises():
    cfg = {"hooks": {"pre-commit": {"min_priority": "urgent"}}}
    with pytest.raises(PriorityError, match="integer"):
        priority_config_for_hook(cfg, "pre-commit")
