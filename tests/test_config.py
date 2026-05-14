"""Tests for hookrunner.config module."""

import textwrap
from pathlib import Path

import pytest

from hookrunner.config import (
    ConfigError,
    find_config_file,
    load_config,
    validate_config,
    DEFAULT_CONFIG_FILENAME,
)


# ---------------------------------------------------------------------------
# find_config_file
# ---------------------------------------------------------------------------

def test_find_config_file_in_current_dir(tmp_path):
    config = tmp_path / DEFAULT_CONFIG_FILENAME
    config.write_text("hooks: {}")
    result = find_config_file(str(tmp_path))
    assert result == config


def test_find_config_file_in_parent_dir(tmp_path):
    config = tmp_path / DEFAULT_CONFIG_FILENAME
    config.write_text("hooks: {}")
    child = tmp_path / "subdir"
    child.mkdir()
    result = find_config_file(str(child))
    assert result == config


def test_find_config_file_returns_none_when_missing(tmp_path):
    result = find_config_file(str(tmp_path))
    assert result is None


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

def test_load_config_success(tmp_path):
    config_file = tmp_path / DEFAULT_CONFIG_FILENAME
    config_file.write_text(textwrap.dedent("""\
        hooks:
          pre-commit:
            - ruff check .
    """))
    data = load_config(config_file)
    assert data == {"hooks": {"pre-commit": ["ruff check ."]}}


def test_load_config_raises_when_file_missing(tmp_path):
    with pytest.raises(ConfigError, match="No '.hookrunner.yml' found"):
        load_config()


def test_load_config_raises_on_invalid_yaml(tmp_path):
    config_file = tmp_path / DEFAULT_CONFIG_FILENAME
    config_file.write_text(": invalid: yaml: [")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(config_file)


def test_load_config_raises_when_top_level_not_mapping(tmp_path):
    config_file = tmp_path / DEFAULT_CONFIG_FILENAME
    config_file.write_text("- just a list")
    with pytest.raises(ConfigError, match="must contain a YAML mapping"):
        load_config(config_file)


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_config_valid():
    validate_config({"hooks": {"pre-commit": ["ruff check .", "pytest"]}})


def test_validate_config_missing_hooks_key():
    with pytest.raises(ConfigError, match="'hooks' key"):
        validate_config({})


def test_validate_config_hooks_not_mapping():
    with pytest.raises(ConfigError, match="must be a mapping"):
        validate_config({"hooks": ["pre-commit"]})


def test_validate_config_commands_not_list():
    with pytest.raises(ConfigError, match="must define a list of commands"):
        validate_config({"hooks": {"pre-commit": "ruff check ."}})


def test_validate_config_command_invalid_type():
    with pytest.raises(ConfigError, match="must be a string or mapping"):
        validate_config({"hooks": {"pre-commit": [42]}})
