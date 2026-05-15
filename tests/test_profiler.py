"""Tests for hookrunner.profiler."""

import time
import pytest
from hookrunner.profiler import CommandProfile, HookProfile, Profiler


def test_command_profile_elapsed():
    cp = CommandProfile(command="echo hi", start_time=1.0, end_time=1.5)
    assert cp.elapsed == pytest.approx(0.5)


def test_command_profile_elapsed_none_when_not_finished():
    cp = CommandProfile(command="echo hi", start_time=1.0)
    assert cp.elapsed is None


def test_command_profile_succeeded_true():
    cp = CommandProfile(command="echo hi", start_time=1.0, end_time=1.1, exit_code=0)
    assert cp.succeeded is True


def test_command_profile_succeeded_false():
    cp = CommandProfile(command="exit 1", start_time=1.0, end_time=1.1, exit_code=1)
    assert cp.succeeded is False


def test_command_profile_succeeded_none_before_end():
    cp = CommandProfile(command="echo hi", start_time=1.0)
    assert cp.succeeded is None


def test_hook_profile_elapsed():
    hp = HookProfile(hook_name="pre-commit", start_time=0.0, end_time=2.0)
    assert hp.elapsed == pytest.approx(2.0)


def test_hook_profile_counts():
    hp = HookProfile(hook_name="pre-commit", start_time=0.0, end_time=1.0)
    hp.commands = [
        CommandProfile("cmd1", 0.0, 0.5, exit_code=0),
        CommandProfile("cmd2", 0.5, 1.0, exit_code=1),
    ]
    assert hp.total_commands == 2
    assert hp.failed_commands == 1


def test_profiler_start_end_hook():
    p = Profiler()
    p.start_hook("pre-commit")
    time.sleep(0.01)
    p.end_hook("pre-commit")
    profile = p.get_hook_profile("pre-commit")
    assert profile is not None
    assert profile.elapsed is not None
    assert profile.elapsed > 0


def test_profiler_start_end_command():
    p = Profiler()
    p.start_hook("pre-push")
    cmd_profile = p.start_command("npm test")
    time.sleep(0.01)
    p.end_command(cmd_profile, exit_code=0)
    p.end_hook("pre-push")
    hook_profile = p.get_hook_profile("pre-push")
    assert len(hook_profile.commands) == 1
    assert hook_profile.commands[0].command == "npm test"
    assert hook_profile.commands[0].exit_code == 0
    assert hook_profile.commands[0].elapsed > 0


def test_profiler_command_without_active_hook_does_not_raise():
    p = Profiler()
    cmd_profile = p.start_command("orphan cmd")
    p.end_command(cmd_profile, exit_code=0)
    assert p.summary() == []


def test_profiler_summary_returns_all_hooks():
    p = Profiler()
    p.start_hook("pre-commit")
    p.end_hook("pre-commit")
    p.start_hook("commit-msg")
    p.end_hook("commit-msg")
    names = [h.hook_name for h in p.summary()]
    assert "pre-commit" in names
    assert "commit-msg" in names


def test_profiler_get_missing_hook_returns_none():
    p = Profiler()
    assert p.get_hook_profile("nonexistent") is None
