"""Tests for hookrunner.glob_matcher."""

import pytest

from hookrunner.glob_matcher import (
    GlobMatcherError,
    command_matches_globs,
    filter_paths,
    match_any,
    parse_patterns,
)


# ---------------------------------------------------------------------------
# parse_patterns
# ---------------------------------------------------------------------------

def test_parse_patterns_none_returns_empty():
    assert parse_patterns(None) == []


def test_parse_patterns_list():
    assert parse_patterns(["*.py", "*.js"]) == ["*.py", "*.js"]


def test_parse_patterns_list_strips_blanks():
    assert parse_patterns(["*.py", "", "  "]) == ["*.py"]


def test_parse_patterns_string_splits_on_whitespace():
    assert parse_patterns("*.py *.js") == ["*.py", "*.js"]


def test_parse_patterns_invalid_type_raises():
    with pytest.raises(GlobMatcherError, match="list or whitespace-separated string"):
        parse_patterns(42)


# ---------------------------------------------------------------------------
# match_any
# ---------------------------------------------------------------------------

def test_match_any_basename_match():
    assert match_any("src/foo.py", ["*.py"]) is True


def test_match_any_full_path_match():
    assert match_any("src/utils.py", ["src/*.py"]) is True


def test_match_any_no_match():
    assert match_any("README.md", ["*.py", "*.js"]) is False


def test_match_any_empty_patterns():
    assert match_any("anything.py", []) is False


def test_match_any_normalises_os_sep(monkeypatch):
    import os
    monkeypatch.setattr(os, "sep", "\\")
    assert match_any("src\\foo.py", ["src/*.py"]) is True


# ---------------------------------------------------------------------------
# filter_paths
# ---------------------------------------------------------------------------

def test_filter_paths_include_only():
    paths = ["a.py", "b.js", "c.md"]
    assert filter_paths(paths, include=["*.py"]) == ["a.py"]


def test_filter_paths_exclude_only():
    paths = ["a.py", "b.js", "c.md"]
    assert filter_paths(paths, exclude=["*.md"]) == ["a.py", "b.js"]


def test_filter_paths_include_and_exclude():
    paths = ["src/a.py", "src/b.py", "tests/test_a.py"]
    result = filter_paths(paths, include=["*.py"], exclude=["test_*.py"])
    assert result == ["src/a.py", "src/b.py"]


def test_filter_paths_no_filters_returns_all():
    paths = ["a.py", "b.js"]
    assert filter_paths(paths) == paths


def test_filter_paths_empty_input():
    assert filter_paths([], include=["*.py"]) == []


# ---------------------------------------------------------------------------
# command_matches_globs
# ---------------------------------------------------------------------------

def test_command_matches_globs_no_patterns_always_true():
    assert command_matches_globs({"run": "lint"}, ["a.py"]) is True


def test_command_matches_globs_include_match():
    cmd = {"run": "lint", "include_patterns": ["*.py"]}
    assert command_matches_globs(cmd, ["foo.py", "bar.md"]) is True


def test_command_matches_globs_include_no_match():
    cmd = {"run": "lint", "include_patterns": ["*.py"]}
    assert command_matches_globs(cmd, ["README.md"]) is False


def test_command_matches_globs_exclude_removes_all():
    cmd = {"run": "lint", "exclude_patterns": ["*.py"]}
    assert command_matches_globs(cmd, ["a.py", "b.py"]) is False


def test_command_matches_globs_string_patterns():
    cmd = {"run": "lint", "include_patterns": "*.py *.ts"}
    assert command_matches_globs(cmd, ["index.ts"]) is True
