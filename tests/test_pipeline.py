"""Tests for hookrunner.pipeline."""

import pytest

from hookrunner.pipeline import (
    PipelineError,
    PipelineResult,
    Stage,
    StageResult,
    build_pipeline_from_config,
    run_pipeline,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ok() -> bool:
    return True


def _fail() -> bool:
    return False


def _raise() -> bool:
    raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# StageResult / PipelineResult
# ---------------------------------------------------------------------------

def test_pipeline_result_passed_when_all_pass():
    pr = PipelineResult(stages=[StageResult("a", True), StageResult("b", True)])
    assert pr.passed is True


def test_pipeline_result_failed_when_one_fails():
    pr = PipelineResult(stages=[StageResult("a", True), StageResult("b", False)])
    assert pr.passed is False


def test_pipeline_result_skipped_ignored_in_passed():
    pr = PipelineResult(stages=[StageResult("a", True), StageResult("b", False, skipped=True)])
    assert pr.passed is True


def test_failed_stages_filters_correctly():
    pr = PipelineResult(stages=[
        StageResult("a", True),
        StageResult("b", False),
        StageResult("c", False, skipped=True),
    ])
    assert [r.name for r in pr.failed_stages] == ["b"]


# ---------------------------------------------------------------------------
# run_pipeline
# ---------------------------------------------------------------------------

def test_run_pipeline_all_pass():
    stages = [Stage("s1", _ok), Stage("s2", _ok)]
    result = run_pipeline(stages)
    assert result.passed is True
    assert all(not r.skipped for r in result.stages)


def test_run_pipeline_aborts_after_failure():
    stages = [Stage("s1", _fail, abort_on_failure=True), Stage("s2", _ok)]
    result = run_pipeline(stages)
    assert result.passed is False
    assert result.stages[1].skipped is True


def test_run_pipeline_continues_when_abort_false():
    stages = [Stage("s1", _fail, abort_on_failure=False), Stage("s2", _ok)]
    result = run_pipeline(stages)
    assert result.stages[0].passed is False
    assert result.stages[1].passed is True
    assert result.stages[1].skipped is False


def test_run_pipeline_captures_exception():
    stages = [Stage("s1", _raise, abort_on_failure=False)]
    result = run_pipeline(stages)
    assert result.stages[0].passed is False
    assert isinstance(result.stages[0].error, RuntimeError)


def test_run_pipeline_exception_aborts_subsequent():
    stages = [Stage("s1", _raise, abort_on_failure=True), Stage("s2", _ok)]
    result = run_pipeline(stages)
    assert result.stages[1].skipped is True


def test_run_pipeline_empty_stages():
    result = run_pipeline([])
    assert result.passed is True
    assert result.stages == []


# ---------------------------------------------------------------------------
# build_pipeline_from_config
# ---------------------------------------------------------------------------

def test_build_pipeline_from_config_creates_stages():
    config = {
        "hooks": {
            "pre-commit": {
                "commands": ["echo hello", "echo world"],
            }
        }
    }
    stages = build_pipeline_from_config("pre-commit", config)
    assert len(stages) == 2
    assert stages[0].name == "echo hello"
    assert stages[1].name == "echo world"


def test_build_pipeline_from_config_missing_hook_returns_empty():
    stages = build_pipeline_from_config("pre-push", {})
    assert stages == []


def test_build_pipeline_from_config_dict_command_uses_name_key():
    config = {
        "hooks": {
            "pre-commit": {
                "commands": [{"name": "lint", "run": "flake8 ."}],
            }
        }
    }
    stages = build_pipeline_from_config("pre-commit", config)
    assert stages[0].name == "lint"
