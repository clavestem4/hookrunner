"""Tests for hookrunner.formatter."""

import io
import pytest
from hookrunner.formatter import (
    Color,
    _supports_color,
    colorize,
    format_hook_header,
    format_command_start,
    format_success,
    format_failure,
    format_warning,
    print_hook_summary,
)


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


class FakePlain(io.StringIO):
    def isatty(self):
        return False


def test_supports_color_tty():
    assert _supports_color(FakeTTY()) is True


def test_supports_color_plain():
    assert _supports_color(FakePlain()) is False


def test_colorize_with_tty():
    stream = FakeTTY()
    result = colorize("hello", Color.RED, stream)
    assert Color.RED.value in result
    assert Color.RESET.value in result
    assert "hello" in result


def test_colorize_without_tty():
    stream = FakePlain()
    result = colorize("hello", Color.RED, stream)
    assert result == "hello"


def test_format_hook_header_plain():
    result = format_hook_header("pre-commit", stream=FakePlain())
    assert "pre-commit" in result
    assert "Running hook" in result


def test_format_command_start_plain():
    result = format_command_start("pytest", stream=FakePlain())
    assert "pytest" in result


def test_format_success_default_plain():
    result = format_success(stream=FakePlain())
    assert "passed" in result.lower() or "All commands" in result


def test_format_success_custom_message():
    result = format_success("Done!", stream=FakePlain())
    assert "Done!" in result


def test_format_failure_plain():
    result = format_failure("Something broke", stream=FakePlain())
    assert "Something broke" in result


def test_format_warning_plain():
    result = format_warning("Deprecated usage", stream=FakePlain())
    assert "Deprecated usage" in result


def test_print_hook_summary_passed(capsys):
    stream = FakePlain()
    print_hook_summary("pre-push", passed=True, stream=stream)
    output = stream.getvalue()
    assert "pre-push" in output
    assert "passed" in output.lower()


def test_print_hook_summary_failed(capsys):
    stream = FakePlain()
    print_hook_summary("pre-push", passed=False, stream=stream)
    output = stream.getvalue()
    assert "pre-push" in output
    assert "failed" in output.lower()
