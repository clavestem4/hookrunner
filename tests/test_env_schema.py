"""Tests for hookrunner.env_schema."""

import pytest

from hookrunner.env_schema import EnvSchema, EnvVarSpec, schema_from_config


# ---------------------------------------------------------------------------
# EnvSchema.validate
# ---------------------------------------------------------------------------


def test_validate_passes_when_all_required_present():
    schema = EnvSchema(specs=[EnvVarSpec(name="TOKEN", required=True)])
    errors = schema.validate({"TOKEN": "abc"})
    assert errors == []


def test_validate_reports_missing_required():
    schema = EnvSchema(specs=[EnvVarSpec(name="SECRET", required=True)])
    errors = schema.validate({})
    assert len(errors) == 1
    assert "SECRET" in errors[0]


def test_validate_includes_description_in_error():
    spec = EnvVarSpec(name="API_KEY", required=True, description="Your API key")
    schema = EnvSchema(specs=[spec])
    errors = schema.validate({})
    assert "Your API key" in errors[0]


def test_validate_optional_missing_no_error():
    schema = EnvSchema(specs=[EnvVarSpec(name="DEBUG", required=False)])
    errors = schema.validate({})
    assert errors == []


def test_validate_required_with_default_no_error_when_missing():
    # If a default is provided the var is effectively optional at runtime.
    spec = EnvVarSpec(name="LOG_LEVEL", required=True, default="INFO")
    schema = EnvSchema(specs=[spec])
    errors = schema.validate({})
    assert errors == []


def test_validate_multiple_missing_returns_all_errors():
    schema = EnvSchema(
        specs=[
            EnvVarSpec(name="A", required=True),
            EnvVarSpec(name="B", required=True),
        ]
    )
    errors = schema.validate({})
    assert len(errors) == 2


# ---------------------------------------------------------------------------
# EnvSchema.apply_defaults
# ---------------------------------------------------------------------------


def test_apply_defaults_fills_missing():
    schema = EnvSchema(specs=[EnvVarSpec(name="ENV", default="production")])
    result = schema.apply_defaults({})
    assert result["ENV"] == "production"


def test_apply_defaults_does_not_override_existing():
    schema = EnvSchema(specs=[EnvVarSpec(name="ENV", default="production")])
    result = schema.apply_defaults({"ENV": "staging"})
    assert result["ENV"] == "staging"


def test_apply_defaults_returns_copy():
    schema = EnvSchema(specs=[EnvVarSpec(name="X", default="1")])
    original = {}
    result = schema.apply_defaults(original)
    assert original == {}
    assert result["X"] == "1"


def test_apply_defaults_no_default_skipped():
    schema = EnvSchema(specs=[EnvVarSpec(name="NO_DEFAULT")])
    result = schema.apply_defaults({})
    assert "NO_DEFAULT" not in result


# ---------------------------------------------------------------------------
# schema_from_config
# ---------------------------------------------------------------------------


def test_schema_from_config_parses_entries():
    config = {
        "env_schema": [
            {"name": "CI", "required": False, "default": "false", "description": "CI flag"}
        ]
    }
    schema = schema_from_config(config)
    assert len(schema.specs) == 1
    spec = schema.specs[0]
    assert spec.name == "CI"
    assert spec.required is False
    assert spec.default == "false"
    assert spec.description == "CI flag"


def test_schema_from_config_empty_when_missing():
    schema = schema_from_config({})
    assert schema.specs == []


def test_schema_from_config_skips_invalid_entries():
    config = {"env_schema": [{"no_name_key": "oops"}, {"name": "VALID"}]}
    schema = schema_from_config(config)
    assert len(schema.specs) == 1
    assert schema.specs[0].name == "VALID"


def test_schema_from_config_non_list_returns_empty():
    config = {"env_schema": {"name": "BAD"}}
    schema = schema_from_config(config)
    assert schema.specs == []
