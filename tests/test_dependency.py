"""Tests for hookrunner.dependency."""

import pytest

from hookrunner.dependency import (
    DependencyError,
    _build_graph,
    _topological_sort,
    resolve_command_order,
)


# ---------------------------------------------------------------------------
# _build_graph
# ---------------------------------------------------------------------------

def test_build_graph_simple():
    cmds = [
        {"name": "lint", "run": "flake8"},
        {"name": "test", "run": "pytest", "depends_on": ["lint"]},
    ]
    graph = _build_graph(cmds)
    assert "test" in graph["lint"]


def test_build_graph_unknown_dep_raises():
    cmds = [{"name": "test", "run": "pytest", "depends_on": ["ghost"]}]
    with pytest.raises(DependencyError, match="unknown command 'ghost'"):
        _build_graph(cmds)


def test_build_graph_ignores_unnamed():
    cmds = [{"run": "echo hi"}, {"name": "lint", "run": "flake8"}]
    graph = _build_graph(cmds)
    assert "lint" in graph
    assert len(graph) == 1


# ---------------------------------------------------------------------------
# _topological_sort
# ---------------------------------------------------------------------------

def test_topological_sort_respects_dependency():
    cmds = [
        {"name": "test", "run": "pytest", "depends_on": ["lint"]},
        {"name": "lint", "run": "flake8"},
    ]
    ordered = _topological_sort(cmds)
    names = [c["name"] for c in ordered]
    assert names.index("lint") < names.index("test")


def test_topological_sort_chain():
    cmds = [
        {"name": "c", "run": "c", "depends_on": ["b"]},
        {"name": "a", "run": "a"},
        {"name": "b", "run": "b", "depends_on": ["a"]},
    ]
    ordered = _topological_sort(cmds)
    names = [c["name"] for c in ordered]
    assert names == ["a", "b", "c"]


def test_topological_sort_detects_cycle():
    cmds = [
        {"name": "a", "run": "a", "depends_on": ["b"]},
        {"name": "b", "run": "b", "depends_on": ["a"]},
    ]
    with pytest.raises(DependencyError, match="Circular dependency"):
        _topological_sort(cmds)


def test_topological_sort_unnamed_appended_last():
    cmds = [
        {"run": "echo unnamed"},
        {"name": "lint", "run": "flake8"},
    ]
    ordered = _topological_sort(cmds)
    assert ordered[-1]["run"] == "echo unnamed"


# ---------------------------------------------------------------------------
# resolve_command_order
# ---------------------------------------------------------------------------

def test_resolve_no_deps_returns_original_order():
    commands = [
        {"name": "b", "run": "b"},
        {"name": "a", "run": "a"},
    ]
    result = resolve_command_order({"commands": commands})
    assert result == commands


def test_resolve_sorts_by_dependency():
    hook_cfg = {
        "commands": [
            {"name": "deploy", "run": "deploy", "depends_on": ["build"]},
            {"name": "build", "run": "build"},
        ]
    }
    result = resolve_command_order(hook_cfg, hook_name="pre-push")
    names = [c["name"] for c in result]
    assert names.index("build") < names.index("deploy")


def test_resolve_prefixes_hook_name_in_error():
    hook_cfg = {
        "commands": [
            {"name": "a", "run": "a", "depends_on": ["missing"]},
        ]
    }
    with pytest.raises(DependencyError, match=r"\[pre-commit\]"):
        resolve_command_order(hook_cfg, hook_name="pre-commit")


def test_resolve_empty_commands():
    assert resolve_command_order({"commands": []}) == []


def test_resolve_missing_commands_key():
    assert resolve_command_order({}) == []
