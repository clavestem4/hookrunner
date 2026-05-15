"""Schema helpers for validating env blocks in hookrunner configs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EnvVarSpec:
    """Describes a single expected environment variable."""

    name: str
    required: bool = True
    default: Optional[str] = None
    description: str = ""


@dataclass
class EnvSchema:
    """Collection of EnvVarSpec entries that define expected env vars."""

    specs: List[EnvVarSpec] = field(default_factory=list)

    def add(self, spec: EnvVarSpec) -> None:
        """Register a new variable spec."""
        self.specs.append(spec)

    def validate(self, env: Dict[str, str]) -> List[str]:
        """Check *env* against specs and return a list of error messages.

        Returns an empty list when all required variables are present.
        """
        errors: List[str] = []
        for spec in self.specs:
            if spec.name not in env:
                if spec.required and spec.default is None:
                    errors.append(
                        f"Required env var '{spec.name}' is missing"
                        + (f": {spec.description}" if spec.description else "")
                    )
        return errors

    def apply_defaults(self, env: Dict[str, str]) -> Dict[str, str]:
        """Return a copy of *env* with default values filled in for missing keys."""
        result = dict(env)
        for spec in self.specs:
            if spec.name not in result and spec.default is not None:
                result[spec.name] = spec.default
        return result


def schema_from_config(config: dict) -> EnvSchema:
    """Build an EnvSchema from the optional ``env_schema`` block in config.

    Expected config shape::

        env_schema:
          - name: CI
            required: false
            default: "false"
            description: Set to 'true' in CI environments

    Returns an empty schema if the block is absent.
    """
    schema = EnvSchema()
    raw = config.get("env_schema", [])
    if not isinstance(raw, list):
        return schema
    for item in raw:
        if not isinstance(item, dict) or "name" not in item:
            continue
        schema.add(
            EnvVarSpec(
                name=str(item["name"]),
                required=bool(item.get("required", True)),
                default=str(item["default"]) if item.get("default") is not None else None,
                description=str(item.get("description", "")),
            )
        )
    return schema
