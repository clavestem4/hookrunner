"""Tests for hookrunner.runner module."""

import pytest
from unittest.mock import patch, MagicMock

from hookrunner.runner import run_hook, HookRunnerError


SAMPLE_CONFIG = {
    "hooks": {
        "pre-commit": ["echo 'running lint'", "echo 'running tests'"],
        "commit-msg": ["echo 'checking message'"],
    }
}


def test_run_hook_success(tmp_path):
    """All commands succeed — run_hook returns 0."""
    with patch("hookrunner.runner.find_config_file", return_value="/fake/.hookrunner.yml"), \
         patch("hookrunner.runner.load_config", return_value=SAMPLE_CONFIG), \
         patch("hookrunner.runner._run_command", return_value=0) as mock_cmd:
        result = run_hook("pre-commit")
        assert result == 0
        assert mock_cmd.call_count == 2


def test_run_hook_fails_on_first_error():
    """run_hook stops and returns non-zero on first failing command."""
    with patch("hookrunner.runner.find_config_file", return_value="/fake/.hookrunner.yml"), \
         patch("hookrunner.runner.load_config", return_value=SAMPLE_CONFIG), \
         patch("hookrunner.runner._run_command", return_value=1) as mock_cmd:
        result = run_hook("pre-commit")
        assert result == 1
        # Should stop after first failure
        assert mock_cmd.call_count == 1


def test_run_hook_no_commands_defined():
    """Hook with no commands returns 0 without running anything."""
    config = {"hooks": {}}
    with patch("hookrunner.runner.find_config_file", return_value="/fake/.hookrunner.yml"), \
         patch("hookrunner.runner.load_config", return_value=config), \
         patch("hookrunner.runner._run_command") as mock_cmd:
        result = run_hook("pre-push")
        assert result == 0
        mock_cmd.assert_not_called()


def test_run_hook_raises_when_no_config_file():
    """run_hook raises HookRunnerError when no config file is found."""
    with patch("hookrunner.runner.find_config_file", return_value=None):
        with pytest.raises(HookRunnerError, match="No .hookrunner.yml config file found"):
            run_hook("pre-commit")


def test_run_hook_raises_on_config_error():
    """run_hook raises HookRunnerError when config loading fails."""
    from hookrunner.config import ConfigError
    with patch("hookrunner.runner.find_config_file", return_value="/fake/.hookrunner.yml"), \
         patch("hookrunner.runner.load_config", side_effect=ConfigError("bad yaml")):
        with pytest.raises(HookRunnerError, match="Failed to load config"):
            run_hook("pre-commit")


def test_run_hook_uses_explicit_config_path():
    """run_hook uses provided config_path instead of searching."""
    with patch("hookrunner.runner.find_config_file") as mock_find, \
         patch("hookrunner.runner.load_config", return_value=SAMPLE_CONFIG), \
         patch("hookrunner.runner._run_command", return_value=0):
        run_hook("pre-commit", config_path="/explicit/.hookrunner.yml")
        mock_find.assert_not_called()
