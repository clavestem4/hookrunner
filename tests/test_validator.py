"""Tests for hookrunner.validator."""

import pytest
from unittest.mock import patch

from hookrunner.validator import (
    ValidationWarning,
    _extract_executable,
    validate_hook_commands,
)


# ---------------------------------------------------------------------------
# _extract_executable
# ---------------------------------------------------------------------------

def test_extract_executable_simple():
    assert _extract_executable("pytest") == "pytest"


def test_extract_executable_with_args():
    assert _extract_executable("black --check .") == "black"


def test_extract_executable_with_path():
    assert _extract_executable("/usr/bin/python3 script.py") == "python3"


def test_extract_executable_env_prefix():
    assert _extract_executable("env PYTHONPATH=. pytest") == "pytest"


def test_extract_executable_empty():
    assert _extract_executable("") == ""


# ---------------------------------------------------------------------------
# validate_hook_commands — valid configs
# ---------------------------------------------------------------------------

def test_validate_hook_commands_all_found():
    config = {"hooks": {"pre-commit": ["pytest", "black --check ."]}}
    with patch("hookrunner.validator.shutil.which", return_value="/usr/bin/pytest"):
        is_valid, warnings = validate_hook_commands(config)
    assert is_valid is True
    assert warnings == []


def test_validate_hook_commands_no_hooks_key():
    is_valid, warnings = validate_hook_commands({})
    assert is_valid is True
    assert warnings == []


def test_validate_hook_commands_empty_hooks():
    is_valid, warnings = validate_hook_commands({"hooks": {}})
    assert is_valid is True
    assert warnings == []


# ---------------------------------------------------------------------------
# validate_hook_commands — warnings (exe not on PATH)
# ---------------------------------------------------------------------------

def test_validate_hook_commands_missing_executable():
    config = {"hooks": {"pre-push": ["nonexistent-tool --flag"]}}
    with patch("hookrunner.validator.shutil.which", return_value=None):
        is_valid, warnings = validate_hook_commands(config)
    assert is_valid is True  # missing exe is a warning, not an error
    assert len(warnings) == 1
    assert "nonexistent-tool" in warnings[0].message
    assert warnings[0].hook == "pre-push"


# ---------------------------------------------------------------------------
# validate_hook_commands — invalid configs
# ---------------------------------------------------------------------------

def test_validate_hook_commands_empty_string_command():
    config = {"hooks": {"pre-commit": [""]}}
    is_valid, warnings = validate_hook_commands(config)
    assert is_valid is False
    assert any("non-empty string" in w.message for w in warnings)


def test_validate_hook_commands_non_list_commands():
    config = {"hooks": {"pre-commit": "pytest"}}
    is_valid, warnings = validate_hook_commands(config)
    assert is_valid is False
    assert any("must be a list" in w.message for w in warnings)


# ---------------------------------------------------------------------------
# ValidationWarning __str__
# ---------------------------------------------------------------------------

def test_validation_warning_str():
    w = ValidationWarning("pre-commit", "bad-cmd", "executable not found on PATH")
    assert "pre-commit" in str(w)
    assert "bad-cmd" in str(w)
    assert "executable not found on PATH" in str(w)
