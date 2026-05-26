"""Tests for hookrunner.dryrun."""

import pytest

from hookrunner.dryrun import (
    DryRunError,
    is_dry_run,
    simulate_hook,
    format_dry_run_output,
)


# ---------------------------------------------------------------------------
# is_dry_run
# ---------------------------------------------------------------------------

def test_is_dry_run_false_by_default():
    assert is_dry_run({}, "pre-commit") is False


def test_is_dry_run_global_true():
    config = {"dry_run": True}
    assert is_dry_run(config, "pre-commit") is True


def test_is_dry_run_global_false_explicit():
    config = {"dry_run": False}
    assert is_dry_run(config, "pre-commit") is False


def test_is_dry_run_hook_level_overrides_global_true():
    config = {
        "dry_run": False,
        "hooks": {"pre-commit": {"dry_run": True}},
    }
    assert is_dry_run(config, "pre-commit") is True


def test_is_dry_run_hook_level_overrides_global_false():
    config = {
        "dry_run": True,
        "hooks": {"pre-commit": {"dry_run": False}},
    }
    assert is_dry_run(config, "pre-commit") is False


def test_is_dry_run_hook_not_in_hooks_falls_back_to_global():
    config = {"dry_run": True, "hooks": {"commit-msg": {"dry_run": False}}}
    assert is_dry_run(config, "pre-commit") is True


def test_is_dry_run_raises_on_non_dict_config():
    with pytest.raises(DryRunError, match="config must be a dict"):
        is_dry_run("bad", "pre-commit")  # type: ignore[arg-type]


def test_is_dry_run_raises_on_empty_hook_name():
    with pytest.raises(DryRunError, match="non-empty"):
        is_dry_run({}, "")


def test_is_dry_run_raises_on_non_bool_global():
    with pytest.raises(DryRunError, match="global dry_run"):
        is_dry_run({"dry_run": "yes"}, "pre-commit")


def test_is_dry_run_raises_on_non_bool_hook_level():
    config = {"hooks": {"pre-commit": {"dry_run": 1}}}
    with pytest.raises(DryRunError, match="hooks.pre-commit.dry_run"):
        is_dry_run(config, "pre-commit")


# ---------------------------------------------------------------------------
# simulate_hook
# ---------------------------------------------------------------------------

def test_simulate_hook_returns_one_record_per_command():
    results = simulate_hook("pre-commit", ["black .", "flake8"])
    assert len(results) == 2


def test_simulate_hook_record_shape():
    results = simulate_hook("pre-commit", ["black ."])
    r = results[0]
    assert r["hook"] == "pre-commit"
    assert r["command"] == "black ."
    assert r["dry_run"] is True
    assert r["returncode"] == 0


def test_simulate_hook_empty_commands():
    results = simulate_hook("pre-commit", [])
    assert results == []


def test_simulate_hook_raises_on_empty_name():
    with pytest.raises(DryRunError, match="non-empty"):
        simulate_hook("", ["echo hi"])


def test_simulate_hook_raises_on_non_list_commands():
    with pytest.raises(DryRunError, match="list"):
        simulate_hook("pre-commit", "echo hi")  # type: ignore[arg-type]


def test_simulate_hook_raises_on_non_string_command():
    with pytest.raises(DryRunError, match="string"):
        simulate_hook("pre-commit", [42])  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# format_dry_run_output
# ---------------------------------------------------------------------------

def test_format_dry_run_output_empty():
    output = format_dry_run_output([])
    assert "No commands" in output


def test_format_dry_run_output_contains_hook_name():
    results = simulate_hook("pre-push", ["pytest"])
    output = format_dry_run_output(results)
    assert "pre-push" in output


def test_format_dry_run_output_lists_commands():
    results = simulate_hook("pre-commit", ["black .", "mypy src"])
    output = format_dry_run_output(results)
    assert "black ." in output
    assert "mypy src" in output


def test_format_dry_run_output_indicates_skipped():
    results = simulate_hook("pre-commit", ["pytest"])
    output = format_dry_run_output(results)
    assert "skipped" in output.lower() or "would run" in output.lower()
