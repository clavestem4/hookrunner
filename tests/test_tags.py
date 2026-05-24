"""Tests for hookrunner.tags"""

import pytest

from hookrunner.tags import (
    TagsError,
    command_matches_tags,
    filter_commands,
    parse_tags,
)


# ---------------------------------------------------------------------------
# parse_tags
# ---------------------------------------------------------------------------

def test_parse_tags_none_returns_empty():
    assert parse_tags(None) == frozenset()


def test_parse_tags_list():
    assert parse_tags(["lint", "fast"]) == frozenset({"lint", "fast"})


def test_parse_tags_list_strips_whitespace():
    assert parse_tags(["  lint ", " fast"]) == frozenset({"lint", "fast"})


def test_parse_tags_list_ignores_blank_strings():
    assert parse_tags(["lint", ""]) == frozenset({"lint"})


def test_parse_tags_csv_string():
    assert parse_tags("lint, fast, security") == frozenset({"lint", "fast", "security"})


def test_parse_tags_single_string():
    assert parse_tags("lint") == frozenset({"lint"})


def test_parse_tags_invalid_type_raises():
    with pytest.raises(TagsError, match="Unsupported tags"):
        parse_tags(42)


def test_parse_tags_list_with_non_string_raises():
    with pytest.raises(TagsError, match="Tag must be a string"):
        parse_tags(["lint", 99])


# ---------------------------------------------------------------------------
# command_matches_tags
# ---------------------------------------------------------------------------

def test_matches_when_active_tags_empty():
    """No filter active → every command passes."""
    assert command_matches_tags(frozenset(), frozenset()) is True
    assert command_matches_tags(frozenset({"lint"}), frozenset()) is True


def test_untagged_command_excluded_when_filter_active():
    assert command_matches_tags(frozenset(), frozenset({"lint"})) is False


def test_any_overlap_sufficient_by_default():
    assert command_matches_tags(frozenset({"lint", "fast"}), frozenset({"fast"})) is True


def test_no_overlap_excluded():
    assert command_matches_tags(frozenset({"security"}), frozenset({"lint"})) is False


def test_require_all_passes_when_superset():
    assert command_matches_tags(
        frozenset({"lint", "fast", "ci"}), frozenset({"lint", "fast"}), require_all=True
    ) is True


def test_require_all_fails_when_missing_tag():
    assert command_matches_tags(
        frozenset({"lint"}), frozenset({"lint", "fast"}), require_all=True
    ) is False


# ---------------------------------------------------------------------------
# filter_commands
# ---------------------------------------------------------------------------

_COMMANDS = [
    {"run": "echo lint", "tags": ["lint"]},
    {"run": "echo security", "tags": "security"},
    {"run": "echo both", "tags": ["lint", "security"]},
    {"run": "echo untagged"},
]


def test_filter_commands_no_active_tags_returns_all():
    result = filter_commands(_COMMANDS, [])
    assert result == _COMMANDS


def test_filter_commands_single_tag():
    result = filter_commands(_COMMANDS, ["lint"])
    runs = [c["run"] for c in result]
    assert "echo lint" in runs
    assert "echo both" in runs
    assert "echo security" not in runs
    assert "echo untagged" not in runs


def test_filter_commands_multiple_tags_any_match():
    result = filter_commands(_COMMANDS, ["lint", "security"])
    assert len(result) == 3  # lint, security, both


def test_filter_commands_require_all():
    result = filter_commands(_COMMANDS, ["lint", "security"], require_all=True)
    runs = [c["run"] for c in result]
    assert runs == ["echo both"]


def test_filter_commands_invalid_entry_raises():
    with pytest.raises(TagsError, match="must be a dict"):
        filter_commands(["not-a-dict"], ["lint"])
