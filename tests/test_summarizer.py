"""Tests for hookrunner.summarizer."""
from __future__ import annotations

import time
import pytest

from hookrunner.profiler import HookProfile, CommandProfile
from hookrunner.validator import ValidationWarning
from hookrunner.summarizer import (
    SummarizerError,
    build_summary,
    format_summary,
    HookSummary,
    CommandSummary,
)


def _make_profile(hook_name="pre-commit", commands=None, passed=True):
    """Create a minimal HookProfile with optional finished CommandProfiles."""
    profile = HookProfile(hook_name=hook_name)
    profile._start = 0.0
    profile._end = 1.5
    profile._passed = passed
    profile._commands = commands or []
    return profile


def _make_cmd(name, elapsed=0.5, succeeded=True):
    cp = CommandProfile(name=name)
    cp._start = 0.0
    cp._end = elapsed
    cp._return_code = 0 if succeeded else 1
    return cp


# ---------------------------------------------------------------------------
# build_summary
# ---------------------------------------------------------------------------

def test_build_summary_returns_hook_summary():
    profile = _make_profile(commands=[_make_cmd("lint")])
    summary = build_summary(profile)
    assert isinstance(summary, HookSummary)


def test_build_summary_hook_name_preserved():
    profile = _make_profile(hook_name="commit-msg")
    summary = build_summary(profile)
    assert summary.hook_name == "commit-msg"


def test_build_summary_passed_flag():
    profile = _make_profile(passed=False)
    summary = build_summary(profile, warnings=[])
    assert summary.passed is False


def test_build_summary_command_count():
    cmds = [_make_cmd("lint"), _make_cmd("test")]
    profile = _make_profile(commands=cmds)
    summary = build_summary(profile)
    assert len(summary.commands) == 2


def test_build_summary_warning_count():
    profile = _make_profile(commands=[_make_cmd("lint")])
    warnings = [
        ValidationWarning(command="lint", message="missing shebang"),
        ValidationWarning(command="lint", message="unknown key 'foo'"),
    ]
    summary = build_summary(profile, warnings=warnings)
    assert summary.warning_count == 2


def test_build_summary_warnings_attached_to_command():
    profile = _make_profile(commands=[_make_cmd("lint")])
    warnings = [ValidationWarning(command="lint", message="unknown key")]
    summary = build_summary(profile, warnings=warnings)
    assert len(summary.commands[0].warnings) == 1


def test_build_summary_warnings_not_mixed_across_commands():
    cmds = [_make_cmd("lint"), _make_cmd("fmt")]
    profile = _make_profile(commands=cmds)
    warnings = [ValidationWarning(command="lint", message="issue")]
    summary = build_summary(profile, warnings=warnings)
    assert len(summary.commands[1].warnings) == 0


def test_build_summary_none_profile_raises():
    with pytest.raises(SummarizerError):
        build_summary(None)


def test_build_summary_no_warnings_defaults_empty():
    profile = _make_profile(commands=[_make_cmd("lint")])
    summary = build_summary(profile)
    assert summary.warning_count == 0


def test_build_summary_as_dict_keys():
    profile = _make_profile(commands=[_make_cmd("lint")])
    d = build_summary(profile).as_dict()
    assert set(d.keys()) == {"hook", "passed", "elapsed", "warning_count", "commands"}


# ---------------------------------------------------------------------------
# format_summary
# ---------------------------------------------------------------------------

def test_format_summary_contains_hook_name():
    profile = _make_profile(hook_name="pre-push")
    text = format_summary(build_summary(profile))
    assert "pre-push" in text


def test_format_summary_passed_label():
    profile = _make_profile(passed=True)
    text = format_summary(build_summary(profile))
    assert "PASSED" in text


def test_format_summary_failed_label():
    profile = _make_profile(passed=False)
    text = format_summary(build_summary(profile))
    assert "FAILED" in text


def test_format_summary_includes_command_name():
    profile = _make_profile(commands=[_make_cmd("mycheck")])
    text = format_summary(build_summary(profile))
    assert "mycheck" in text


def test_format_summary_includes_warning_text():
    profile = _make_profile(commands=[_make_cmd("lint")])
    warnings = [ValidationWarning(command="lint", message="bad key")]
    text = format_summary(build_summary(profile, warnings=warnings))
    assert "bad key" in text
