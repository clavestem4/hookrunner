"""Tests for the hookrunner CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hookrunner.cli import build_parser, main
from hookrunner.installer import InstallerError
from hookrunner.runner import HookRunnerError


def test_build_parser_install():
    parser = build_parser()
    args = parser.parse_args(["install"])
    assert args.command == "install"
    assert "pre-commit" in args.hooks


def test_build_parser_install_custom_hooks():
    parser = build_parser()
    args = parser.parse_args(["install", "--hooks", "pre-commit", "pre-push"])
    assert args.hooks == ["pre-commit", "pre-push"]


def test_build_parser_uninstall():
    parser = build_parser()
    args = parser.parse_args(["uninstall", "--hooks", "pre-commit"])
    assert args.command == "uninstall"
    assert args.hooks == ["pre-commit"]


def test_build_parser_run():
    parser = build_parser()
    args = parser.parse_args(["run", "pre-commit"])
    assert args.command == "run"
    assert args.hook == "pre-commit"


def test_build_parser_no_command_exits():
    """Verify that invoking the parser with no subcommand raises SystemExit."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_main_install_success(tmp_path):
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)

    with patch("hookrunner.cli.find_git_hooks_dir", return_value=hooks_dir) as mock_find, \
         patch("hookrunner.cli.install_hooks") as mock_install, \
         patch("hookrunner.cli.Path.cwd", return_value=tmp_path):
        result = main(["install", "--hooks", "pre-commit"])

    assert result == 0
    mock_install.assert_called_once_with(hooks_dir, ["pre-commit"])


def test_main_uninstall_success(tmp_path):
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)

    with patch("hookrunner.cli.find_git_hooks_dir", return_value=hooks_dir), \
         patch("hookrunner.cli.uninstall_hooks", return_value=1) as mock_uninstall, \
         patch("hookrunner.cli.Path.cwd", return_value=tmp_path):
        result = main(["uninstall", "--hooks", "pre-commit"])

    assert result == 0
    mock_uninstall.assert_called_once()


def test_main_run_success(tmp_path):
    with patch("hookrunner.cli.run_hook") as mock_run, \
         patch("hookrunner.cli.Path.cwd", return_value=tmp_path):
        result = main(["run", "pre-commit"])

    assert result == 0
    mock_run.assert_called_once_with("pre-commit", cwd=tmp_path)


def test_main_returns_1_on_installer_error(tmp_path):
    with patch("hookrunner.cli.find_git_hooks_dir", side_effect=InstallerError("no git repo")), \
         patch("hookrunner.cli.Path.cwd", return_value=tmp_path):
        result = main(["install"])

    assert result == 1


def test_main_returns_1_on_hook_runner_error(tmp_path):
    with patch("hookrunner.cli.run_hook", side_effect=HookRunnerError("hook failed")), \
         patch("hookrunner.cli.Path.cwd", return_value=tmp_path):
        result = main(["run", "pre-commit"])

    assert result == 1


def test_main_uninstall_returns_1_on_installer_error(tmp_path):
    """Verify that an InstallerError during uninstall is handled and returns 1."""
    with patch("hookrunner.cli.find_git_hooks_dir", side_effect=InstallerError("no git repo")), \
         patch("hookrunner.cli.Path.cwd", return_value=tmp_path):
        result = main(["uninstall", "--hooks", "pre-commit"])

    assert result == 1
