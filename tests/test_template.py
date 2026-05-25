"""Tests for hookrunner.template."""

from __future__ import annotations

import os
import pytest

from hookrunner.template import (
    TemplateError,
    extract_variables,
    render,
    render_commands,
)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def test_render_no_placeholders():
    assert render("echo hello") == "echo hello"


def test_render_single_placeholder_from_context():
    assert render("echo {MSG}", {"MSG": "hi"}) == "echo hi"


def test_render_multiple_placeholders_from_context():
    result = render("{CMD} {ARG}", {"CMD": "lint", "ARG": "--fix"})
    assert result == "lint --fix"


def test_render_falls_back_to_environment(monkeypatch):
    monkeypatch.setenv("HR_BRANCH", "main")
    assert render("deploy {HR_BRANCH}") == "deploy main"


def test_render_context_overrides_environment(monkeypatch):
    monkeypatch.setenv("TARGET", "staging")
    assert render("deploy {TARGET}", {"TARGET": "prod"}) == "deploy prod"


def test_render_raises_on_unresolved_placeholder():
    with pytest.raises(TemplateError, match="UNKNOWN"):
        render("echo {UNKNOWN}")


def test_render_raises_lists_all_missing_variables():
    with pytest.raises(TemplateError) as exc_info:
        render("{FOO} {BAR}", {})
    msg = str(exc_info.value)
    assert "BAR" in msg
    assert "FOO" in msg


def test_render_empty_string():
    assert render("") == ""


def test_render_none_context_uses_env(monkeypatch):
    monkeypatch.setenv("TOOL", "ruff")
    assert render("run {TOOL}", None) == "run ruff"


# ---------------------------------------------------------------------------
# render_commands
# ---------------------------------------------------------------------------

def test_render_commands_renders_all():
    ctx = {"ENV": "ci"}
    cmds = ["echo {ENV}", "pytest --env {ENV}"]
    assert render_commands(cmds, ctx) == ["echo ci", "pytest --env ci"]


def test_render_commands_raises_on_first_unresolved():
    with pytest.raises(TemplateError):
        render_commands(["echo {MISSING}", "echo ok"])


def test_render_commands_empty_list():
    assert render_commands([]) == []


# ---------------------------------------------------------------------------
# extract_variables
# ---------------------------------------------------------------------------

def test_extract_variables_none():
    assert extract_variables("echo hello") == []


def test_extract_variables_single():
    assert extract_variables("echo {MSG}") == ["MSG"]


def test_extract_variables_multiple_sorted():
    result = extract_variables("{CMD} {ARG} {CMD}")
    assert result == ["ARG", "CMD"]


def test_extract_variables_empty_string():
    assert extract_variables("") == []
