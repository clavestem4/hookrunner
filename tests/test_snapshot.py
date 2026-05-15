"""Tests for hookrunner.snapshot."""

from pathlib import Path

import pytest

from hookrunner.registry import HookEntry, HookRegistry
from hookrunner.snapshot import (
    SnapshotError,
    default_snapshot_path,
    diff_registries,
    load_snapshot,
    save_snapshot,
)


def _make_registry(*entries: HookEntry) -> HookRegistry:
    reg = HookRegistry()
    for e in entries:
        reg.register(e)
    return reg


def test_default_snapshot_path_uses_cwd():
    path = default_snapshot_path()
    assert path.name == ".hookrunner_registry.json"
    assert path.parent == Path.cwd()


def test_default_snapshot_path_custom_base(tmp_path):
    path = default_snapshot_path(tmp_path)
    assert path == tmp_path / ".hookrunner_registry.json"


def test_save_and_load_roundtrip(tmp_path):
    entry = HookEntry(
        name="pre-commit",
        script_path=tmp_path / ".git/hooks/pre-commit",
        commands=["flake8 ."],
        enabled=True,
    )
    reg = _make_registry(entry)
    snap_path = tmp_path / "snap.json"
    save_snapshot(reg, snap_path)
    loaded = load_snapshot(snap_path)
    result = loaded.get("pre-commit")
    assert result is not None
    assert result.commands == ["flake8 ."]
    assert result.enabled is True


def test_load_snapshot_missing_file(tmp_path):
    with pytest.raises(SnapshotError, match="not found"):
        load_snapshot(tmp_path / "nonexistent.json")


def test_load_snapshot_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not-json", encoding="utf-8")
    with pytest.raises(SnapshotError):
        load_snapshot(bad)


def test_load_snapshot_malformed_entry(tmp_path):
    import json
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"no_name": True}]), encoding="utf-8")
    with pytest.raises(SnapshotError, match="missing key"):
        load_snapshot(bad)


def test_save_snapshot_bad_path():
    bad_path = Path("/nonexistent_dir/snap.json")
    reg = HookRegistry()
    with pytest.raises(SnapshotError, match="Failed to write"):
        save_snapshot(reg, bad_path)


def test_diff_registries_added():
    old = _make_registry()
    new = _make_registry(HookEntry(name="pre-commit", script_path=Path(".git/hooks/pre-commit")))
    diff = diff_registries(old, new)
    assert "pre-commit" in diff["added"]
    assert diff["removed"] == []


def test_diff_registries_removed():
    old = _make_registry(HookEntry(name="pre-push", script_path=Path(".git/hooks/pre-push")))
    new = _make_registry()
    diff = diff_registries(old, new)
    assert "pre-push" in diff["removed"]


def test_diff_registries_changed():
    old = _make_registry(HookEntry(name="pre-commit", script_path=Path(".git/hooks/pre-commit"), commands=["flake8"]))
    new = _make_registry(HookEntry(name="pre-commit", script_path=Path(".git/hooks/pre-commit"), commands=["pytest"]))
    diff = diff_registries(old, new)
    assert "pre-commit" in diff["changed"]


def test_diff_registries_no_changes():
    entry = HookEntry(name="pre-commit", script_path=Path(".git/hooks/pre-commit"))
    old = _make_registry(entry)
    new = _make_registry(HookEntry(name="pre-commit", script_path=Path(".git/hooks/pre-commit")))
    diff = diff_registries(old, new)
    assert diff == {"added": [], "removed": [], "changed": []}
