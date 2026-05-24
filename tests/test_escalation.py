"""Tests for hookrunner.escalation."""

import pytest

from hookrunner.escalation import (
    EscalationError,
    EscalationLevel,
    escalation_config_for_hook,
    get_escalation_level,
    should_abort,
    should_warn,
)


# ---------------------------------------------------------------------------
# get_escalation_level
# ---------------------------------------------------------------------------

class TestGetEscalationLevel:
    def test_command_level_takes_precedence(self):
        cmd = {"on_failure": "warn"}
        hook = {"on_failure": "error"}
        glbl = {"on_failure": "fatal"}
        assert get_escalation_level(cmd, hook, glbl) == "warn"

    def test_hook_level_over_global(self):
        cmd = {}
        hook = {"on_failure": "fatal"}
        glbl = {"on_failure": "warn"}
        assert get_escalation_level(cmd, hook, glbl) == "fatal"

    def test_global_level_when_no_command_or_hook(self):
        assert get_escalation_level({}, {}, {"on_failure": "warn"}) == "warn"

    def test_default_is_error_when_nothing_set(self):
        assert get_escalation_level({}, {}, {}) == "error"

    def test_case_insensitive(self):
        assert get_escalation_level({"on_failure": "WARN"}, {}, {}) == "warn"

    def test_invalid_level_raises(self):
        with pytest.raises(EscalationError, match="Invalid escalation level"):
            get_escalation_level({"on_failure": "explode"}, {}, {})

    def test_invalid_level_in_hook_raises(self):
        with pytest.raises(EscalationError):
            get_escalation_level({}, {"on_failure": "ignore"}, {})


# ---------------------------------------------------------------------------
# should_abort
# ---------------------------------------------------------------------------

class TestShouldAbort:
    def test_error_aborts(self):
        assert should_abort(EscalationLevel.ERROR) is True

    def test_fatal_aborts(self):
        assert should_abort(EscalationLevel.FATAL) is True

    def test_warn_does_not_abort(self):
        assert should_abort(EscalationLevel.WARN) is False

    def test_invalid_level_raises(self):
        with pytest.raises(EscalationError):
            should_abort("continue")


# ---------------------------------------------------------------------------
# should_warn
# ---------------------------------------------------------------------------

class TestShouldWarn:
    def test_warn_level_returns_true(self):
        assert should_warn(EscalationLevel.WARN) is True

    def test_error_returns_false(self):
        assert should_warn(EscalationLevel.ERROR) is False

    def test_fatal_returns_false(self):
        assert should_warn(EscalationLevel.FATAL) is False

    def test_invalid_level_raises(self):
        with pytest.raises(EscalationError):
            should_warn("skip")


# ---------------------------------------------------------------------------
# escalation_config_for_hook
# ---------------------------------------------------------------------------

class TestEscalationConfigForHook:
    def test_returns_hook_level_when_set(self):
        config = {
            "on_failure": "warn",
            "hooks": {"pre-commit": {"on_failure": "fatal"}},
        }
        result = escalation_config_for_hook("pre-commit", config)
        assert result["resolved"] == "fatal"
        assert result["hook"] == "fatal"
        assert result["global"] == "warn"

    def test_falls_back_to_global(self):
        config = {"on_failure": "warn", "hooks": {}}
        result = escalation_config_for_hook("pre-push", config)
        assert result["resolved"] == "warn"
        assert result["hook"] is None

    def test_defaults_to_error_when_nothing_set(self):
        result = escalation_config_for_hook("commit-msg", {})
        assert result["resolved"] == "error"
        assert result["global"] is None
        assert result["hook"] is None

    def test_missing_hook_name_falls_back_gracefully(self):
        config = {"hooks": {"pre-commit": {"on_failure": "fatal"}}}
        result = escalation_config_for_hook("post-merge", config)
        assert result["hook"] is None
        assert result["resolved"] == "error"
