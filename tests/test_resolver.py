"""Tests for hookrunner.resolver module."""

import os
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hookrunner.resolver import (
    ResolverError,
    fetch_remote_config,
    load_local_shared_config,
    merge_configs,
    resolve_config,
)


# ---------------------------------------------------------------------------
# fetch_remote_config
# ---------------------------------------------------------------------------

def test_fetch_remote_config_success():
    payload = yaml.dump({"pre-commit": ["flake8"]}).encode()
    mock_response = MagicMock()
    mock_response.read.return_value = payload
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = fetch_remote_config("https://example.com/hooks.yml")

    assert result == {"pre-commit": ["flake8"]}


def test_fetch_remote_config_url_error():
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        with pytest.raises(ResolverError, match="Failed to fetch remote config"):
            fetch_remote_config("https://example.com/hooks.yml")


def test_fetch_remote_config_invalid_yaml():
    mock_response = MagicMock()
    mock_response.read.return_value = b": invalid: yaml: ["
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        with pytest.raises(ResolverError, match="Failed to parse remote config"):
            fetch_remote_config("https://example.com/hooks.yml")


# ---------------------------------------------------------------------------
# load_local_shared_config
# ---------------------------------------------------------------------------

def test_load_local_shared_config_success(tmp_path):
    cfg_file = tmp_path / "shared.yml"
    cfg_file.write_text(yaml.dump({"pre-push": ["pytest"]}))

    result = load_local_shared_config(str(cfg_file))
    assert result == {"pre-push": ["pytest"]}


def test_load_local_shared_config_missing_file():
    with pytest.raises(ResolverError, match="not found"):
        load_local_shared_config("/nonexistent/path/shared.yml")


def test_load_local_shared_config_not_a_mapping(tmp_path):
    cfg_file = tmp_path / "bad.yml"
    cfg_file.write_text("- just\n- a\n- list\n")

    with pytest.raises(ResolverError, match="not a valid mapping"):
        load_local_shared_config(str(cfg_file))


# ---------------------------------------------------------------------------
# merge_configs
# ---------------------------------------------------------------------------

def test_merge_configs_combines_hooks():
    base = {"pre-commit": ["black", "isort"]}
    override = {"pre-commit": ["mypy"], "pre-push": ["pytest"]}

    result = merge_configs(base, override)

    assert result["pre-commit"] == ["black", "isort", "mypy"]
    assert result["pre-push"] == ["pytest"]


def test_merge_configs_override_only_hook():
    base = {}
    override = {"commit-msg": ["check-msg"]}

    result = merge_configs(base, override)
    assert result == {"commit-msg": ["check-msg"]}


# ---------------------------------------------------------------------------
# resolve_config
# ---------------------------------------------------------------------------

def test_resolve_config_no_extends():
    config = {"pre-commit": ["flake8"]}
    result = resolve_config(config)
    assert result == {"pre-commit": ["flake8"]}


def test_resolve_config_with_local_extends(tmp_path):
    shared_file = tmp_path / "shared.yml"
    shared_file.write_text(yaml.dump({"pre-commit": ["black"]}))

    config = {"extends": str(shared_file), "pre-commit": ["isort"]}
    result = resolve_config(config)

    assert "extends" not in result
    assert result["pre-commit"] == ["black", "isort"]


def test_resolve_config_with_remote_extends():
    payload = yaml.dump({"pre-commit": ["remote-lint"]}).encode()
    mock_response = MagicMock()
    mock_response.read.return_value = payload
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    config = {"extends": "https://example.com/shared.yml", "pre-commit": ["local-lint"]}

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = resolve_config(config)

    assert "extends" not in result
    assert result["pre-commit"] == ["remote-lint", "local-lint"]
