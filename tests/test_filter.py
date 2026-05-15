"""Tests for hookrunner.filter."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from hookrunner.filter import (
    FilterError,
    match_branch,
    match_files,
    should_run_hook,
    current_branch,
)


# ---------------------------------------------------------------------------
# current_branch
# ---------------------------------------------------------------------------

def test_current_branch_returns_string(tmp_path, monkeypatch):
    with patch("hookrunner.filter.subprocess.run") as mock_run:
        mock_run.return_value.stdout = "main\n"
        mock_run.return_value.returncode = 0
        assert current_branch() == "main"


def test_current_branch_returns_none_on_error():
    with patch("hookrunner.filter.subprocess.run", side_effect=FileNotFoundError):
        assert current_branch() is None


# ---------------------------------------------------------------------------
# match_branch
# ---------------------------------------------------------------------------

def test_match_branch_exact():
    assert match_branch("main", "main") is True


def test_match_branch_glob():
    assert match_branch("feature/*", "feature/login") is True


def test_match_branch_no_match():
    assert match_branch("main", "develop") is False


def test_match_branch_none_branch_returns_false():
    with patch("hookrunner.filter.current_branch", return_value=None):
        assert match_branch("main") is False


# ---------------------------------------------------------------------------
# match_files
# ---------------------------------------------------------------------------

def test_match_files_by_extension():
    assert match_files(["*.py"], ["src/foo.py", "README.md"]) is True


def test_match_files_no_match():
    assert match_files(["*.js"], ["src/foo.py"]) is False


def test_match_files_empty_staged():
    assert match_files(["*.py"], []) is False


def test_match_files_full_path_pattern():
    assert match_files(["src/*.py"], ["src/main.py"]) is True


def test_match_files_uses_git_when_none(monkeypatch):
    with patch("hookrunner.filter._get_staged_files", return_value=["app.py"]):
        assert match_files(["*.py"]) is True


# ---------------------------------------------------------------------------
# should_run_hook
# ---------------------------------------------------------------------------

def test_should_run_hook_no_filter():
    assert should_run_hook({}) is True


def test_should_run_hook_branch_match():
    config = {"filter": {"branches": ["main", "release/*"]}}
    assert should_run_hook(config, branch="main") is True


def test_should_run_hook_branch_no_match():
    config = {"filter": {"branches": ["main"]}}
    assert should_run_hook(config, branch="develop") is False


def test_should_run_hook_files_match():
    config = {"filter": {"files": ["*.py"]}}
    assert should_run_hook(config, staged_files=["app.py"]) is True


def test_should_run_hook_files_no_match():
    config = {"filter": {"files": ["*.py"]}}
    assert should_run_hook(config, staged_files=["README.md"]) is False


def test_should_run_hook_env_match(monkeypatch):
    monkeypatch.setenv("CI", "true")
    config = {"filter": {"env": {"CI": "true"}}}
    assert should_run_hook(config) is True


def test_should_run_hook_env_no_match(monkeypatch):
    monkeypatch.setenv("CI", "false")
    config = {"filter": {"env": {"CI": "true"}}}
    assert should_run_hook(config) is False


def test_should_run_hook_combined_all_pass(monkeypatch):
    monkeypatch.setenv("STAGE", "prod")
    config = {
        "filter": {
            "branches": ["main"],
            "files": ["*.py"],
            "env": {"STAGE": "prod"},
        }
    }
    assert should_run_hook(config, branch="main", staged_files=["app.py"]) is True


def test_should_run_hook_combined_one_fails(monkeypatch):
    monkeypatch.setenv("STAGE", "dev")
    config = {
        "filter": {
            "branches": ["main"],
            "env": {"STAGE": "prod"},
        }
    }
    assert should_run_hook(config, branch="main") is False
