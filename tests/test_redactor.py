"""Tests for hookrunner.redactor."""

import pytest

from hookrunner.redactor import (
    REDACTED,
    RedactorError,
    build_redact_set,
    redact_env,
    redact_string,
)

SAMPLE_ENV = {
    "DATABASE_PASSWORD": "s3cr3t",
    "API_TOKEN": "tok_abc123",
    "HOME": "/home/user",
    "PATH": "/usr/bin:/bin",
    "MY_SECRET": "shh",
    "NORMAL_VAR": "hello",
}


def test_build_redact_set_finds_defaults():
    sensitive = build_redact_set(SAMPLE_ENV)
    assert "DATABASE_PASSWORD" in sensitive
    assert "API_TOKEN" in sensitive
    assert "MY_SECRET" in sensitive


def test_build_redact_set_ignores_safe_keys():
    sensitive = build_redact_set(SAMPLE_ENV)
    assert "HOME" not in sensitive
    assert "PATH" not in sensitive
    assert "NORMAL_VAR" not in sensitive


def test_build_redact_set_extra_pattern():
    env = {"DEPLOY_USER": "alice", "SAFE": "ok"}
    sensitive = build_redact_set(env, extra_patterns=[r"(?i)user"])
    assert "DEPLOY_USER" in sensitive
    assert "SAFE" not in sensitive


def test_build_redact_set_invalid_pattern_raises():
    with pytest.raises(RedactorError, match="Invalid redact pattern"):
        build_redact_set({"X": "1"}, extra_patterns=["[invalid"])


def test_redact_env_replaces_sensitive_values():
    result = redact_env(SAMPLE_ENV)
    assert result["DATABASE_PASSWORD"] == REDACTED
    assert result["API_TOKEN"] == REDACTED
    assert result["MY_SECRET"] == REDACTED


def test_redact_env_preserves_safe_values():
    result = redact_env(SAMPLE_ENV)
    assert result["HOME"] == "/home/user"
    assert result["NORMAL_VAR"] == "hello"


def test_redact_env_does_not_mutate_original():
    original = dict(SAMPLE_ENV)
    redact_env(original)
    assert original["DATABASE_PASSWORD"] == "s3cr3t"


def test_redact_string_removes_secret_value():
    env = {"API_TOKEN": "tok_abc123"}
    text = "Authorization: Bearer tok_abc123"
    result = redact_string(text, env)
    assert "tok_abc123" not in result
    assert REDACTED in result


def test_redact_string_leaves_safe_text_unchanged():
    env = {"HOME": "/home/user"}
    text = "Running from /home/user/project"
    result = redact_string(text, env)
    assert result == text


def test_redact_string_multiple_occurrences():
    env = {"MY_SECRET": "shh"}
    text = "shh and again shh"
    result = redact_string(text, env)
    assert "shh" not in result
    assert result.count(REDACTED) == 2


def test_redact_string_empty_value_not_replaced():
    env = {"API_TOKEN": ""}
    text = "nothing to replace here"
    result = redact_string(text, env)
    assert result == text
