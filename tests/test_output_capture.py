"""Tests for hookrunner.output_capture."""
import pytest

from hookrunner.output_capture import (
    CapturedOutput,
    HookOutput,
    OutputCaptureError,
    capture_output,
    collect_hook_output,
)


# ---------------------------------------------------------------------------
# CapturedOutput
# ---------------------------------------------------------------------------

def test_captured_output_combined_both():
    c = CapturedOutput(command="lint", stdout="ok", stderr="warn")
    assert c.combined == "ok\nwarn"


def test_captured_output_combined_stdout_only():
    c = CapturedOutput(command="lint", stdout="ok", stderr="")
    assert c.combined == "ok"


def test_captured_output_combined_empty():
    c = CapturedOutput(command="lint")
    assert c.combined == ""


def test_captured_output_has_output_true():
    c = CapturedOutput(command="lint", stdout="hello")
    assert c.has_output is True


def test_captured_output_has_output_false():
    c = CapturedOutput(command="lint")
    assert c.has_output is False


# ---------------------------------------------------------------------------
# capture_output helper
# ---------------------------------------------------------------------------

def test_capture_output_strips_trailing_newline():
    c = capture_output("mycommand", "line\n", "err\n", 0)
    assert c.stdout == "line"
    assert c.stderr == "err"
    assert c.returncode == 0


def test_capture_output_empty_command_raises():
    with pytest.raises(OutputCaptureError, match="command must not be empty"):
        capture_output("", "out", "err", 0)


# ---------------------------------------------------------------------------
# HookOutput
# ---------------------------------------------------------------------------

def _make_hook_output():
    ho = HookOutput(hook_name="pre-commit")
    ho.add(CapturedOutput(command="flake8", stdout="", stderr="", returncode=0))
    ho.add(CapturedOutput(command="mypy", stdout="", stderr="error: bad type", returncode=1))
    return ho


def test_hook_output_failed_entries():
    ho = _make_hook_output()
    failed = ho.failed_entries()
    assert len(failed) == 1
    assert failed[0].command == "mypy"


def test_hook_output_format_summary_hides_passing_by_default():
    ho = _make_hook_output()
    summary = ho.format_summary()
    assert "mypy" in summary
    assert "flake8" not in summary


def test_hook_output_format_summary_shows_passing_when_requested():
    ho = _make_hook_output()
    summary = ho.format_summary(show_passing=True)
    assert "flake8" in summary
    assert "mypy" in summary


def test_hook_output_format_summary_includes_stderr():
    ho = _make_hook_output()
    summary = ho.format_summary()
    assert "error: bad type" in summary


def test_hook_output_format_summary_header():
    ho = HookOutput(hook_name="pre-push")
    assert ho.format_summary().startswith("[pre-push]")


# ---------------------------------------------------------------------------
# collect_hook_output
# ---------------------------------------------------------------------------

def test_collect_hook_output_bundles_entries():
    captures = [
        capture_output("cmd1", "a", "", 0),
        capture_output("cmd2", "", "e", 1),
    ]
    ho = collect_hook_output("pre-commit", captures)
    assert ho.hook_name == "pre-commit"
    assert len(ho.entries) == 2


def test_collect_hook_output_empty_name_raises():
    with pytest.raises(OutputCaptureError, match="hook_name must not be empty"):
        collect_hook_output("", [])


def test_collect_hook_output_empty_list():
    ho = collect_hook_output("post-merge", [])
    assert ho.entries == []
    assert ho.failed_entries() == []
