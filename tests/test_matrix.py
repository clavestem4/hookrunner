"""Tests for hookrunner.matrix."""

import pytest

from hookrunner.matrix import MatrixError, expand_commands, parse_matrix


# ---------------------------------------------------------------------------
# parse_matrix
# ---------------------------------------------------------------------------

def _cfg(matrix_block):
    return {"hooks": {"test": {"matrix": matrix_block}}}


def test_parse_matrix_returns_single_empty_dict_when_no_matrix():
    config = {"hooks": {"test": {}}}
    result = parse_matrix(config, "test")
    assert result == [{}]


def test_parse_matrix_missing_hook_returns_single_empty_dict():
    result = parse_matrix({"hooks": {}}, "nonexistent")
    assert result == [{}]


def test_parse_matrix_single_variable():
    result = parse_matrix(_cfg({"python": ["3.10", "3.11"]}), "test")
    assert result == [{"python": "3.10"}, {"python": "3.11"}]


def test_parse_matrix_two_variables_cartesian_product():
    result = parse_matrix(_cfg({"py": ["3.10", "3.11"], "os": ["linux", "macos"]}), "test")
    assert len(result) == 4
    assert {"py": "3.10", "os": "linux"} in result
    assert {"py": "3.11", "os": "macos"} in result


def test_parse_matrix_numeric_values_allowed():
    result = parse_matrix(_cfg({"workers": [1, 2, 4]}), "test")
    assert result == [{"workers": 1}, {"workers": 2}, {"workers": 4}]


def test_parse_matrix_not_a_dict_raises():
    with pytest.raises(MatrixError, match="must be a mapping"):
        parse_matrix(_cfg(["3.10", "3.11"]), "test")


def test_parse_matrix_empty_list_raises():
    with pytest.raises(MatrixError, match="non-empty list"):
        parse_matrix(_cfg({"python": []}), "test")


def test_parse_matrix_non_list_value_raises():
    with pytest.raises(MatrixError, match="non-empty list"):
        parse_matrix(_cfg({"python": "3.10"}), "test")


def test_parse_matrix_non_scalar_in_list_raises():
    with pytest.raises(MatrixError, match="non-scalar"):
        parse_matrix(_cfg({"python": [["3.10"]]}), "test")


def test_parse_matrix_three_variables():
    result = parse_matrix(
        _cfg({"a": ["x"], "b": ["y"], "c": ["z"]}), "test"
    )
    assert result == [{"a": "x", "b": "y", "c": "z"}]


# ---------------------------------------------------------------------------
# expand_commands
# ---------------------------------------------------------------------------

def test_expand_commands_substitutes_variable():
    cmds = ["tox -e py{python}"]
    result = expand_commands(cmds, {"python": "310"})
    assert result == ["tox -e py310"]


def test_expand_commands_multiple_variables():
    cmds = ["echo {os} {python}"]
    result = expand_commands(cmds, {"os": "linux", "python": "3.11"})
    assert result == ["echo linux 3.11"]


def test_expand_commands_unknown_placeholder_left_intact():
    cmds = ["echo {unknown}"]
    result = expand_commands(cmds, {"python": "3.10"})
    assert result == ["echo {unknown}"]


def test_expand_commands_no_placeholders_unchanged():
    cmds = ["pytest tests/"]
    result = expand_commands(cmds, {"python": "3.10"})
    assert result == ["pytest tests/"]


def test_expand_commands_empty_bindings_leaves_commands_intact():
    cmds = ["make lint", "make test"]
    result = expand_commands(cmds, {})
    assert result == ["make lint", "make test"]


def test_expand_commands_multiple_commands_all_expanded():
    cmds = ["echo {env}", "run --env {env}"]
    result = expand_commands(cmds, {"env": "staging"})
    assert result == ["echo staging", "run --env staging"]
