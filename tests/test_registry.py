"""Tests for hookrunner.registry."""

from pathlib import Path

import pytest

from hookrunner.registry import HookEntry, HookRegistry, RegistryError


@pytest.fixture()
def registry() -> HookRegistry:
    return HookRegistry()


@pytest.fixture()
def sample_entry() -> HookEntry:
    return HookEntry(
        name="pre-commit",
        script_path=Path(".git/hooks/pre-commit"),
        commands=["flake8 .", "pytest"],
    )


def test_register_and_get(registry, sample_entry):
    registry.register(sample_entry)
    result = registry.get("pre-commit")
    assert result is sample_entry


def test_get_missing_returns_none(registry):
    assert registry.get("pre-push") is None


def test_unregister_removes_entry(registry, sample_entry):
    registry.register(sample_entry)
    registry.unregister("pre-commit")
    assert registry.get("pre-commit") is None


def test_unregister_missing_raises(registry):
    with pytest.raises(RegistryError, match="not registered"):
        registry.unregister("pre-push")


def test_list_hooks_sorted(registry):
    registry.register(HookEntry(name="pre-push", script_path=Path(".git/hooks/pre-push")))
    registry.register(HookEntry(name="pre-commit", script_path=Path(".git/hooks/pre-commit")))
    names = [e.name for e in registry.list_hooks()]
    assert names == ["pre-commit", "pre-push"]


def test_enabled_hooks_filters_disabled(registry):
    registry.register(HookEntry(name="pre-commit", script_path=Path(".git/hooks/pre-commit")))
    registry.register(HookEntry(name="pre-push", script_path=Path(".git/hooks/pre-push"), enabled=False))
    enabled = [e.name for e in registry.enabled_hooks()]
    assert enabled == ["pre-commit"]


def test_disable_hook(registry, sample_entry):
    registry.register(sample_entry)
    registry.disable("pre-commit")
    assert registry.get("pre-commit").enabled is False


def test_enable_hook(registry, sample_entry):
    sample_entry.enabled = False
    registry.register(sample_entry)
    registry.enable("pre-commit")
    assert registry.get("pre-commit").enabled is True


def test_disable_missing_raises(registry):
    with pytest.raises(RegistryError):
        registry.disable("commit-msg")


def test_enable_missing_raises(registry):
    with pytest.raises(RegistryError):
        registry.enable("commit-msg")


def test_build_from_config(registry, tmp_path):
    config = {
        "hooks": {
            "pre-commit": ["flake8 .", "pytest"],
            "pre-push": ["mypy hookrunner"],
        }
    }
    hooks_dir = tmp_path / ".git" / "hooks"
    registry.build_from_config(config, hooks_dir)
    assert registry.get("pre-commit") is not None
    assert registry.get("pre-push").commands == ["mypy hookrunner"]


def test_hook_entry_to_dict(sample_entry):
    d = sample_entry.to_dict()
    assert d["name"] == "pre-commit"
    assert d["enabled"] is True
    assert "flake8 ." in d["commands"]
