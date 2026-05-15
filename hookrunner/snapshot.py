"""Snapshot support: persist and restore the hook registry to/from disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from hookrunner.registry import HookEntry, HookRegistry, RegistryError

SNAPSHOT_FILENAME = ".hookrunner_registry.json"


class SnapshotError(Exception):
    """Raised when snapshot read/write fails."""


def default_snapshot_path(base_dir: Optional[Path] = None) -> Path:
    """Return the default path for the registry snapshot file."""
    base = base_dir or Path.cwd()
    return base / SNAPSHOT_FILENAME


def save_snapshot(registry: HookRegistry, path: Path) -> None:
    """Serialize the registry to a JSON snapshot file."""
    data = [entry.to_dict() for entry in registry.list_hooks()]
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:
        raise SnapshotError(f"Failed to write snapshot to {path}: {exc}") from exc


def load_snapshot(path: Path) -> HookRegistry:
    """Deserialize a JSON snapshot file into a HookRegistry."""
    if not path.exists():
        raise SnapshotError(f"Snapshot file not found: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"Failed to read snapshot from {path}: {exc}") from exc

    registry = HookRegistry()
    for item in data:
        try:
            entry = HookEntry(
                name=item["name"],
                script_path=Path(item["script_path"]),
                commands=item.get("commands", []),
                enabled=item.get("enabled", True),
            )
            registry.register(entry)
        except KeyError as exc:
            raise SnapshotError(f"Malformed snapshot entry, missing key: {exc}") from exc
    return registry


def diff_registries(old: HookRegistry, new: HookRegistry) -> dict:
    """Return a dict describing added, removed, and changed hooks."""
    old_names = {e.name for e in old.list_hooks()}
    new_names = {e.name for e in new.list_hooks()}
    added = sorted(new_names - old_names)
    removed = sorted(old_names - new_names)
    changed = []
    for name in sorted(old_names & new_names):
        old_entry = old.get(name)
        new_entry = new.get(name)
        if old_entry.to_dict() != new_entry.to_dict():
            changed.append(name)
    return {"added": added, "removed": removed, "changed": changed}
