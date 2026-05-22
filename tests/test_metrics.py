"""Tests for hookrunner.metrics."""

import pytest
from hookrunner.metrics import (
    CommandMetric,
    HookMetric,
    MetricsCollector,
    MetricsError,
    get_collector,
)


@pytest.fixture()
def collector() -> MetricsCollector:
    c = MetricsCollector()
    return c


def test_record_command_stores_entry(collector):
    collector.record_command("pre-commit", "flake8 .", 1.2, 0)
    cmds = collector.commands_for_hook("pre-commit")
    assert len(cmds) == 1
    assert cmds[0].command == "flake8 ."
    assert cmds[0].duration == pytest.approx(1.2)
    assert cmds[0].exit_code == 0


def test_command_metric_succeeded_true(collector):
    collector.record_command("pre-commit", "flake8 .", 0.5, 0)
    assert collector.commands_for_hook("pre-commit")[0].succeeded is True


def test_command_metric_succeeded_false(collector):
    collector.record_command("pre-commit", "flake8 .", 0.5, 1)
    assert collector.commands_for_hook("pre-commit")[0].succeeded is False


def test_record_command_raises_on_empty_hook(collector):
    with pytest.raises(MetricsError):
        collector.record_command("", "flake8 .", 1.0, 0)


def test_record_command_raises_on_empty_command(collector):
    with pytest.raises(MetricsError):
        collector.record_command("pre-commit", "", 1.0, 0)


def test_record_hook_stores_entry(collector):
    collector.record_hook("pre-commit", 2.5, 3, 0)
    summary = collector.summary()
    assert summary["total_hooks"] == 1
    assert summary["passed"] == 1
    assert summary["failed"] == 0


def test_hook_metric_passed_false_when_failures(collector):
    collector.record_hook("pre-commit", 1.0, 2, 1)
    summary = collector.summary()
    assert summary["failed"] == 1
    assert summary["passed"] == 0


def test_record_hook_raises_on_empty_name(collector):
    with pytest.raises(MetricsError):
        collector.record_hook("", 1.0, 1, 0)


def test_summary_avg_duration(collector):
    collector.record_hook("pre-commit", 2.0, 1, 0)
    collector.record_hook("pre-push", 4.0, 1, 0)
    summary = collector.summary()
    assert summary["avg_hook_duration"] == pytest.approx(3.0)


def test_summary_empty_collector(collector):
    summary = collector.summary()
    assert summary["total_hooks"] == 0
    assert summary["avg_hook_duration"] is None


def test_commands_for_hook_filters_by_hook(collector):
    collector.record_command("pre-commit", "flake8 .", 0.5, 0)
    collector.record_command("pre-push", "pytest", 3.0, 0)
    assert len(collector.commands_for_hook("pre-commit")) == 1
    assert len(collector.commands_for_hook("pre-push")) == 1
    assert len(collector.commands_for_hook("commit-msg")) == 0


def test_reset_clears_all(collector):
    collector.record_command("pre-commit", "flake8 .", 0.5, 0)
    collector.record_hook("pre-commit", 0.5, 1, 0)
    collector.reset()
    assert collector.summary()["total_hooks"] == 0
    assert collector.commands_for_hook("pre-commit") == []


def test_get_collector_returns_singleton():
    c1 = get_collector()
    c2 = get_collector()
    assert c1 is c2
