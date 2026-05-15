"""Tests for hookrunner.pipeline_report."""

import pytest

from hookrunner.pipeline import PipelineResult, StageResult
from hookrunner.pipeline_report import format_pipeline_report


def _make_result(*stages):
    """Helper: build PipelineResult from (name, passed, skipped) tuples."""
    return PipelineResult(
        stages=[
            StageResult(name=n, passed=p, skipped=s)
            for n, p, s in stages
        ]
    )


def test_format_report_contains_hook_name():
    result = _make_result(("lint", True, False))
    report = format_pipeline_report("pre-commit", result, use_color=False)
    assert "pre-commit" in report


def test_format_report_pass_label():
    result = _make_result(("lint", True, False))
    report = format_pipeline_report("pre-commit", result, use_color=False)
    assert "PASS" in report
    assert "lint" in report


def test_format_report_fail_label():
    result = _make_result(("lint", False, False))
    report = format_pipeline_report("pre-commit", result, use_color=False)
    assert "FAIL" in report


def test_format_report_skipped_label():
    result = _make_result(("typecheck", True, True))
    report = format_pipeline_report("pre-commit", result, use_color=False)
    assert "SKIPPED" in report


def test_format_report_summary_all_passed():
    result = _make_result(("a", True, False), ("b", True, False))
    report = format_pipeline_report("pre-commit", result, use_color=False)
    assert "All stages passed" in report


def test_format_report_summary_failures():
    result = _make_result(("a", False, False), ("b", False, False))
    report = format_pipeline_report("pre-commit", result, use_color=False)
    assert "2 stage(s) failed" in report


def test_format_report_error_shown():
    stage = StageResult(name="mytest", passed=False, error=RuntimeError("oops"))
    result = PipelineResult(stages=[stage])
    report = format_pipeline_report("pre-commit", result, use_color=False)
    assert "oops" in report


def test_format_report_no_color_has_no_ansi():
    result = _make_result(("lint", True, False))
    report = format_pipeline_report("pre-commit", result, use_color=False)
    assert "\x1b[" not in report


def test_format_report_with_color_has_ansi():
    result = _make_result(("lint", True, False))
    report = format_pipeline_report("pre-commit", result, use_color=True)
    assert "\x1b[" in report
