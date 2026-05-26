"""Tests for hookrunner.truncator."""

import pytest

from hookrunner.truncator import (
    TruncatorError,
    DEFAULT_TAIL_LINES,
    OMISSION_MARKER,
    get_max_lines,
    get_tail_lines,
    truncate_lines,
    truncate_text,
)


# ---------------------------------------------------------------------------
# get_max_lines
# ---------------------------------------------------------------------------

def test_get_max_lines_returns_none_when_not_set():
    assert get_max_lines({}) is None


def test_get_max_lines_global():
    assert get_max_lines({"truncate_lines": 100}) == 100


def test_get_max_lines_hook_overrides_global():
    config = {
        "truncate_lines": 100,
        "hooks": {"pre-commit": {"truncate_lines": 50}},
    }
    assert get_max_lines(config, "pre-commit") == 50


def test_get_max_lines_coerces_string():
    assert get_max_lines({"truncate_lines": "75"}) == 75


def test_get_max_lines_raises_on_non_integer():
    with pytest.raises(TruncatorError, match="truncate_lines must be an integer"):
        get_max_lines({"truncate_lines": "abc"})


def test_get_max_lines_raises_when_less_than_one():
    with pytest.raises(TruncatorError, match=">= 1"):
        get_max_lines({"truncate_lines": 0})


# ---------------------------------------------------------------------------
# get_tail_lines
# ---------------------------------------------------------------------------

def test_get_tail_lines_default_when_not_set():
    assert get_tail_lines({}) == DEFAULT_TAIL_LINES


def test_get_tail_lines_global():
    assert get_tail_lines({"truncate_tail_lines": 10}) == 10


def test_get_tail_lines_hook_overrides_global():
    config = {
        "truncate_tail_lines": 10,
        "hooks": {"pre-push": {"truncate_tail_lines": 5}},
    }
    assert get_tail_lines(config, "pre-push") == 5


def test_get_tail_lines_zero_allowed():
    assert get_tail_lines({"truncate_tail_lines": 0}) == 0


def test_get_tail_lines_raises_on_negative():
    with pytest.raises(TruncatorError, match=">= 0"):
        get_tail_lines({"truncate_tail_lines": -1})


# ---------------------------------------------------------------------------
# truncate_lines
# ---------------------------------------------------------------------------

def test_truncate_lines_no_truncation_needed():
    lines = ["a", "b", "c"]
    assert truncate_lines(lines, max_lines=10) == lines


def test_truncate_lines_exact_max_no_truncation():
    lines = list(map(str, range(5)))
    assert truncate_lines(lines, max_lines=5) == lines


def test_truncate_lines_inserts_marker():
    lines = list(map(str, range(100)))
    result = truncate_lines(lines, max_lines=10, tail_lines=3)
    # head: 7, marker: 1, tail: 3  => 11 items
    assert len(result) == 11
    assert "omitted" in result[7]
    assert result[-3:] == ["97", "98", "99"]
    assert result[:7] == ["0", "1", "2", "3", "4", "5", "6"]


def test_truncate_lines_zero_tail():
    lines = list(map(str, range(50)))
    result = truncate_lines(lines, max_lines=5, tail_lines=0)
    assert len(result) == 6  # 5 head lines + 1 marker
    assert "omitted" in result[5]


def test_truncate_lines_raises_on_invalid_max():
    with pytest.raises(TruncatorError, match="max_lines must be >= 1"):
        truncate_lines(["x"], max_lines=0)


def test_truncate_lines_raises_on_negative_tail():
    with pytest.raises(TruncatorError, match="tail_lines must be >= 0"):
        truncate_lines(["x"], max_lines=5, tail_lines=-1)


# ---------------------------------------------------------------------------
# truncate_text
# ---------------------------------------------------------------------------

def test_truncate_text_short_text_unchanged():
    text = "line1\nline2\nline3"
    assert truncate_text(text, max_lines=10) == text


def test_truncate_text_long_text_truncated():
    text = "\n".join(str(i) for i in range(200))
    result = truncate_text(text, max_lines=50, tail_lines=10)
    result_lines = result.splitlines()
    assert len(result_lines) == 51  # 40 head + marker + 10 tail
    assert "omitted" in result_lines[40]
