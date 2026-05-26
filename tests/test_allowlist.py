"""Tests for hookrunner.allowlist."""

import pytest

from hookrunner.allowlist import (
    AllowlistError,
    _extract_executable,
    _get_allowlist,
    check_commands,
    filter_commands,
    is_allowed,
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
    assert _extract_executable("ENV=1 DEBUG=true myapp run") == "myapp"


def test_extract_executable_empty():
    assert _extract_executable("") == ""


# ---------------------------------------------------------------------------
# _get_allowlist
# ---------------------------------------------------------------------------

def test_get_allowlist_global():
    cfg = {"allowlist": ["black", "pytest"]}
    assert _get_allowlist(cfg) == ["black", "pytest"]


def test_get_allowlist_hook_overrides_global():
    cfg = {
        "allowlist": ["black"],
        "hooks": {"pre-commit": {"allowlist": ["flake8"]}},
    }
    assert _get_allowlist(cfg, "pre-commit") == ["flake8"]


def test_get_allowlist_falls_back_to_global_when_hook_has_none():
    cfg = {
        "allowlist": ["black"],
        "hooks": {"pre-commit": {}},
    }
    assert _get_allowlist(cfg, "pre-commit") == ["black"]


def test_get_allowlist_returns_none_when_not_configured():
    assert _get_allowlist({}) is None


def test_get_allowlist_strips_blank_entries():
    cfg = {"allowlist": ["black", "", "  ", "pytest"]}
    result = _get_allowlist(cfg)
    assert "" not in result
    assert "  " not in result
    assert "black" in result


# ---------------------------------------------------------------------------
# is_allowed
# ---------------------------------------------------------------------------

def test_is_allowed_returns_true_when_no_allowlist():
    assert is_allowed("anything", {}) is True


def test_is_allowed_true_for_listed_command():
    cfg = {"allowlist": ["pytest"]}
    assert is_allowed("pytest -x tests/", cfg) is True


def test_is_allowed_false_for_unlisted_command():
    cfg = {"allowlist": ["pytest"]}
    assert is_allowed("rm -rf /", cfg) is False


# ---------------------------------------------------------------------------
# filter_commands
# ---------------------------------------------------------------------------

def test_filter_commands_keeps_allowed():
    cfg = {"allowlist": ["pytest", "black"]}
    cmds = ["pytest tests/", "black .", "rm -rf /"]
    assert filter_commands(cmds, cfg) == ["pytest tests/", "black ."]


def test_filter_commands_returns_all_when_no_allowlist():
    cmds = ["pytest", "rm -rf /"]
    assert filter_commands(cmds, {}) == cmds


# ---------------------------------------------------------------------------
# check_commands
# ---------------------------------------------------------------------------

def test_check_commands_passes_when_all_allowed():
    cfg = {"allowlist": ["pytest", "black"]}
    check_commands(["pytest -x", "black --check ."], cfg)  # no exception


def test_check_commands_raises_on_blocked_command():
    cfg = {"allowlist": ["pytest"]}
    with pytest.raises(AllowlistError, match="rm"):
        check_commands(["pytest", "rm -rf /"], cfg)


def test_check_commands_no_allowlist_always_passes():
    check_commands(["rm -rf /", "curl evil.com"], {})  # no exception


def test_check_commands_error_mentions_hook_name():
    cfg = {
        "hooks": {"pre-push": {"allowlist": ["pytest"]}},
    }
    with pytest.raises(AllowlistError, match="pre-push"):
        check_commands(["curl http://example.com"], cfg, hook_name="pre-push")
