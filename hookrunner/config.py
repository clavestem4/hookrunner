"""Configuration loader for hookrunner.

Supports loading hook configurations from a local `.hookrunner.yml` file
or a remote shareable config referenced by URL or package name.
"""

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_FILENAME = ".hookrunner.yml"


class ConfigError(Exception):
    """Raised when the configuration is invalid or cannot be loaded."""


def find_config_file(start_dir: str | None = None) -> Path | None:
    """Walk up the directory tree to find a .hookrunner.yml file."""
    current = Path(start_dir or os.getcwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / DEFAULT_CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load and parse the hookrunner YAML configuration.

    Args:
        config_path: Explicit path to the config file. If None, the config
                     file is discovered automatically.

    Returns:
        Parsed configuration dictionary.

    Raises:
        ConfigError: If the file is missing, unreadable, or malformed.
    """
    path = config_path or find_config_file()
    if path is None:
        raise ConfigError(
            f"No '{DEFAULT_CONFIG_FILENAME}' found in the current directory or any parent."
        )

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except OSError as exc:
        raise ConfigError(f"Cannot read config file '{path}': {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Config file '{path}' must contain a YAML mapping at the top level.")

    return data


def validate_config(config: dict[str, Any]) -> None:
    """Perform basic structural validation on the loaded config.

    Raises:
        ConfigError: If required keys are missing or values have wrong types.
    """
    hooks_section = config.get("hooks")
    if hooks_section is None:
        raise ConfigError("Config must contain a top-level 'hooks' key.")
    if not isinstance(hooks_section, dict):
        raise ConfigError("'hooks' must be a mapping of hook-name -> list of commands.")

    for hook_name, commands in hooks_section.items():
        if not isinstance(commands, list):
            raise ConfigError(
                f"Hook '{hook_name}' must define a list of commands, got {type(commands).__name__}."
            )
        for i, cmd in enumerate(commands):
            if not isinstance(cmd, (str, dict)):
                raise ConfigError(
                    f"Hook '{hook_name}', command #{i + 1} must be a string or mapping."
                )
