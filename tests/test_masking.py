"""Tests for hookrunner.masking."""

import pytest

from hookrunner.masking import (
    MaskingError,
    MASK_PLACEHOLDER,
    build_mask_patterns,
    mask_env,
    mask_text,
)


# ---------------------------------------------------------------------------
# build_mask_patterns
# ---------------------------------------------------------------------------

def test_build_mask_patterns_global_values():
    config = {"mask": {"values": ["secret", "token123"]}}
    patterns = build_mask_patterns(config)
    assert len(patterns) == 2


def test_build_mask_patterns_hook_specific():
    config = {
        "mask": {"values": ["global_secret"]},
        "hooks": {"pre-commit": {"mask": {"values": ["hook_secret"]}}},
    }
    patterns = build_mask_patterns(config, hook_name="pre-commit")
    assert len(patterns) == 2


def test_build_mask_patterns_no_mask_section():
    patterns = build_mask_patterns({})
    assert patterns == []


def test_build_mask_patterns_skips_blank_values():
    config = {"mask": {"values": ["", "  ", "real_secret"]}}
    patterns = build_mask_patterns(config)
    assert len(patterns) == 1


def test_build_mask_patterns_invalid_global_raises():
    with pytest.raises(MaskingError, match="must be a list"):
        build_mask_patterns({"mask": {"values": "not-a-list"}})


def test_build_mask_patterns_invalid_hook_raises():
    config = {
        "hooks": {"pre-push": {"mask": {"values": "bad"}}},
    }
    with pytest.raises(MaskingError, match="must be a list"):
        build_mask_patterns(config, hook_name="pre-push")


def test_build_mask_patterns_numeric_value_coerced():
    config = {"mask": {"values": [12345]}}
    patterns = build_mask_patterns(config)
    assert len(patterns) == 1


# ---------------------------------------------------------------------------
# mask_text
# ---------------------------------------------------------------------------

def test_mask_text_replaces_single_occurrence():
    config = {"mask": {"values": ["hunter2"]}}
    patterns = build_mask_patterns(config)
    result = mask_text("password is hunter2 ok", patterns)
    assert "hunter2" not in result
    assert MASK_PLACEHOLDER in result


def test_mask_text_replaces_multiple_occurrences():
    config = {"mask": {"values": ["abc"]}}
    patterns = build_mask_patterns(config)
    result = mask_text("abc and abc and abc", patterns)
    assert result == f"{MASK_PLACEHOLDER} and {MASK_PLACEHOLDER} and {MASK_PLACEHOLDER}"


def test_mask_text_no_patterns_returns_unchanged():
    text = "nothing to hide"
    assert mask_text(text, []) == text


def test_mask_text_special_regex_chars_escaped():
    config = {"mask": {"values": ["my.secret+token"]}}
    patterns = build_mask_patterns(config)
    result = mask_text("value=my.secret+token!", patterns)
    assert "my.secret+token" not in result
    assert MASK_PLACEHOLDER in result


def test_mask_text_partial_match_not_affected():
    config = {"mask": {"values": ["SECRET"]}}
    patterns = build_mask_patterns(config)
    result = mask_text("MY_SECRET_KEY is safe", patterns)
    # literal match only — 'SECRET' substring inside 'MY_SECRET_KEY' is replaced
    assert "SECRET" not in result


# ---------------------------------------------------------------------------
# mask_env
# ---------------------------------------------------------------------------

def test_mask_env_replaces_matching_values():
    config = {"mask": {"values": ["topsecret"]}}
    patterns = build_mask_patterns(config)
    env = {"API_KEY": "topsecret", "HOME": "/home/user"}
    masked = mask_env(env, patterns)
    assert masked["API_KEY"] == MASK_PLACEHOLDER
    assert masked["HOME"] == "/home/user"


def test_mask_env_does_not_mutate_original():
    config = {"mask": {"values": ["pw"]}}
    patterns = build_mask_patterns(config)
    env = {"PASS": "pw"}
    masked = mask_env(env, patterns)
    assert env["PASS"] == "pw"
    assert masked["PASS"] == MASK_PLACEHOLDER


def test_mask_env_empty_env():
    config = {"mask": {"values": ["x"]}}
    patterns = build_mask_patterns(config)
    assert mask_env({}, patterns) == {}
