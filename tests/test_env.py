"""Tests for hookrunner.env."""

import os

import pytest

from hookrunner.env import EnvError, build_env, load_env_block


# ---------------------------------------------------------------------------
# load_env_block
# ---------------------------------------------------------------------------


def test_load_env_block_global_only():
    config = {"env": {"FOO": "bar"}, "hooks": {}}
    result = load_env_block(config, "pre-commit")
    assert result == {"FOO": "bar"}


def test_load_env_block_hook_only():
    config = {"hooks": {"pre-commit": {"env": {"HOOK_VAR": "1"}}}}
    result = load_env_block(config, "pre-commit")
    assert result == {"HOOK_VAR": "1"}


def test_load_env_block_hook_overrides_global():
    config = {
        "env": {"LEVEL": "global", "SHARED": "yes"},
        "hooks": {"pre-push": {"env": {"LEVEL": "hook"}}},
    }
    result = load_env_block(config, "pre-push")
    assert result["LEVEL"] == "hook"
    assert result["SHARED"] == "yes"


def test_load_env_block_empty_config():
    result = load_env_block({}, "pre-commit")
    assert result == {}


def test_load_env_block_numeric_value_coerced():
    config = {"env": {"WORKERS": 4}}
    result = load_env_block(config, "pre-commit")
    assert result["WORKERS"] == "4"


def test_load_env_block_bool_value_coerced():
    config = {"env": {"DEBUG": True}}
    result = load_env_block(config, "pre-commit")
    assert result["DEBUG"] == "True"


def test_load_env_block_raises_on_non_dict_global():
    config = {"env": ["FOO=bar"]}
    with pytest.raises(EnvError, match="global"):
        load_env_block(config, "pre-commit")


def test_load_env_block_raises_on_non_dict_hook():
    config = {"hooks": {"pre-commit": {"env": "FOO=bar"}}}
    with pytest.raises(EnvError, match="pre-commit"):
        load_env_block(config, "pre-commit")


def test_load_env_block_raises_on_list_value():
    config = {"env": {"BAD": ["a", "b"]}}
    with pytest.raises(EnvError, match="BAD"):
        load_env_block(config, "pre-commit")


def test_load_env_block_raises_on_non_string_key():
    config = {"env": {123: "value"}}
    with pytest.raises(EnvError, match="must be a string"):
        load_env_block(config, "pre-commit")


# ---------------------------------------------------------------------------
# build_env
# ---------------------------------------------------------------------------


def test_build_env_uses_os_environ_by_default():
    env = build_env(overrides={"MY_KEY": "hello"})
    assert env["MY_KEY"] == "hello"
    assert "PATH" in env  # inherited from os.environ


def test_build_env_overrides_base_key():
    base = {"FOO": "original", "BAR": "keep"}
    env = build_env(base=base, overrides={"FOO": "new"})
    assert env["FOO"] == "new"
    assert env["BAR"] == "keep"


def test_build_env_no_overrides_returns_copy_of_base():
    base = {"A": "1"}
    env = build_env(base=base)
    assert env == base
    assert env is not base


def test_build_env_empty_overrides_noop():
    base = {"X": "y"}
    env = build_env(base=base, overrides={})
    assert env == base


def test_build_env_does_not_mutate_base():
    base = {"ORIG": "value"}
    build_env(base=base, overrides={"NEW": "injected"})
    assert "NEW" not in base
