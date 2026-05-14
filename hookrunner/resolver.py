"""Resolve and merge shareable hook configurations from remote or local sources."""

import os
import urllib.request
import urllib.error
from typing import Optional

import yaml


class ResolverError(Exception):
    """Raised when a shared config cannot be resolved."""


def fetch_remote_config(url: str) -> dict:
    """Fetch a YAML hook config from a remote URL.

    Args:
        url: HTTP/HTTPS URL pointing to a .hookrunner.yml file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        ResolverError: If the URL cannot be fetched or parsed.
    """
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise ResolverError(f"Failed to fetch remote config from '{url}': {exc}") from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ResolverError(f"Failed to parse remote config from '{url}': {exc}") from exc

    if not isinstance(data, dict):
        raise ResolverError(f"Remote config at '{url}' is not a valid mapping.")

    return data


def load_local_shared_config(path: str) -> dict:
    """Load a shared config from a local file path.

    Args:
        path: Absolute or relative path to a YAML config file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        ResolverError: If the file cannot be read or parsed.
    """
    if not os.path.isfile(path):
        raise ResolverError(f"Shared config file not found: '{path}'")

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        raise ResolverError(f"Failed to load shared config from '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ResolverError(f"Shared config at '{path}' is not a valid mapping.")

    return data


def merge_configs(base: dict, override: dict) -> dict:
    """Merge two hook configs; override hooks are appended after base hooks.

    For each hook type (e.g. 'pre-commit'), commands from *override* are
    appended to those already defined in *base*.

    Args:
        base: The primary (local) configuration.
        override: The shared configuration whose hooks are merged in.

    Returns:
        A new merged configuration dictionary.
    """
    merged = {k: list(v) for k, v in base.items() if isinstance(v, list)}

    for hook, commands in override.items():
        if not isinstance(commands, list):
            continue
        if hook in merged:
            merged[hook] = merged[hook] + commands
        else:
            merged[hook] = list(commands)

    return merged


def resolve_config(config: dict) -> dict:
    """Resolve any 'extends' key in *config* and return the merged result.

    If the config contains an 'extends' key with a URL or local path, the
    referenced config is fetched/loaded and merged with the local config.
    The 'extends' key is removed from the returned dict.

    Args:
        config: Parsed local configuration dictionary.

    Returns:
        Configuration with shared hooks merged in.

    Raises:
        ResolverError: If the shared config cannot be loaded.
    """
    extends = config.get("extends")
    if not extends:
        return {k: v for k, v in config.items() if k != "extends"}

    if isinstance(extends, str) and extends.startswith(("http://", "https://")):
        shared = fetch_remote_config(extends)
    else:
        shared = load_local_shared_config(str(extends))

    local = {k: v for k, v in config.items() if k != "extends"}
    return merge_configs(shared, local)
