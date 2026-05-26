"""Tests for hookrunner.skip."""

import pytest

from hookrunner.skip import (
    SkipError,
    filter_commands,
    is_skip_all,
    should_skip_command,
    should_skip_hook,
)


# ---------------------------------------------------------------------------
# is_skip_all
# ---------------------------------------------------------------------------


def test_is_skip_all_false_by_default():
    assert is_skip_all({}) is False


@pytest.mark.parametrize("val", ["1", "true", "True", "TRUE", "yes", "YES"])
def test_is_skip_all_truthy_values(val):
    assert is_skip_all({"HOOKRUNNER_SKIP": val}) is True


@pytest.mark.parametrize("val", ["0", "false", "no", "", "maybe"])
def test_is_skip_all_falsy_values(val):
    assert is_skip_all({"HOOKRUNNER_SKIP": val}) is False


# ---------------------------------------------------------------------------
# should_skip_hook
# ---------------------------------------------------------------------------


def test_should_skip_hook_false_when_no_skip():
    config = {"hooks": {"pre-commit": {"commands": []}}}
    assert should_skip_hook("pre-commit", config) is False


def test_should_skip_hook_global_true():
    config = {"skip": True, "hooks": {"pre-commit": {}}}
    assert should_skip_hook("pre-commit", config) is True


def test_should_skip_hook_global_string_true():
    config = {"skip": "true", "hooks": {"pre-commit": {}}}
    assert should_skip_hook("pre-commit", config) is True


def test_should_skip_hook_per_hook_true():
    config = {"hooks": {"pre-commit": {"skip": True}}}
    assert should_skip_hook("pre-commit", config) is True


def test_should_skip_hook_per_hook_string_true():
    config = {"hooks": {"pre-commit": {"skip": "yes"}}}
    assert should_skip_hook("pre-commit", config) is True


def test_should_skip_hook_per_hook_false_explicit():
    config = {"hooks": {"pre-commit": {"skip": False}}}
    assert should_skip_hook("pre-commit", config) is False


def test_should_skip_hook_missing_hook_key():
    config = {"hooks": {}}
    assert should_skip_hook("pre-push", config) is False


def test_should_skip_hook_invalid_skip_value_raises():
    config = {"hooks": {"pre-commit": {"skip": 42}}}
    with pytest.raises(SkipError):
        should_skip_hook("pre-commit", config)


# ---------------------------------------------------------------------------
# should_skip_command
# ---------------------------------------------------------------------------


def test_should_skip_command_false_when_no_skip():
    assert should_skip_command({"run": "echo hi"}) is False


def test_should_skip_command_true_bool():
    assert should_skip_command({"run": "echo hi", "skip": True}) is True


def test_should_skip_command_true_string():
    assert should_skip_command({"run": "echo hi", "skip": "1"}) is True


def test_should_skip_command_false_string():
    assert should_skip_command({"run": "echo hi", "skip": "false"}) is False


def test_should_skip_command_invalid_type_raises():
    with pytest.raises(SkipError):
        should_skip_command({"run": "echo hi", "skip": 3.14})


def test_should_skip_command_non_dict_raises():
    with pytest.raises(SkipError):
        should_skip_command("echo hi")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# filter_commands
# ---------------------------------------------------------------------------


def test_filter_commands_removes_skipped():
    cmds = [
        {"run": "echo a"},
        {"run": "echo b", "skip": True},
        {"run": "echo c"},
    ]
    result = filter_commands(cmds)
    assert len(result) == 2
    assert all(c["run"] != "echo b" for c in result)


def test_filter_commands_empty_list():
    assert filter_commands([]) == []


def test_filter_commands_all_skipped():
    cmds = [{"run": "x", "skip": True}, {"run": "y", "skip": "yes"}]
    assert filter_commands(cmds) == []


def test_filter_commands_none_skipped():
    cmds = [{"run": "a"}, {"run": "b", "skip": False}]
    assert filter_commands(cmds) == cmds
