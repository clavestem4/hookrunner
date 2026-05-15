"""Checkpoint support for resuming interrupted hook runs."""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

CHECKPOINT_DIR = ".hookrunner_checkpoints"


class CheckpointError(Exception):
    pass


def _checkpoint_path(hook_name: str, base: Optional[Path] = None) -> Path:
    base = base or Path.cwd()
    return base / CHECKPOINT_DIR / f"{hook_name}.json"


def save_checkpoint(hook_name: str, completed: List[str], base: Optional[Path] = None) -> Path:
    """Persist the list of completed commands for a hook run."""
    path = _checkpoint_path(hook_name, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "hook": hook_name,
        "completed": completed,
        "saved_at": time.time(),
    }
    try:
        path.write_text(json.dumps(record, indent=2))
    except OSError as exc:
        raise CheckpointError(f"Could not save checkpoint: {exc}") from exc
    return path


def load_checkpoint(hook_name: str, base: Optional[Path] = None) -> Optional[List[str]]:
    """Return completed commands from a previous run, or None if no checkpoint exists."""
    path = _checkpoint_path(hook_name, base)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"Could not read checkpoint: {exc}") from exc
    if data.get("hook") != hook_name:
        raise CheckpointError(f"Checkpoint hook mismatch: expected {hook_name!r}")
    return data.get("completed", [])


def clear_checkpoint(hook_name: str, base: Optional[Path] = None) -> bool:
    """Remove the checkpoint file for a hook.  Returns True if a file was removed."""
    path = _checkpoint_path(hook_name, base)
    if path.exists():
        path.unlink()
        return True
    return False


def pending_commands(all_commands: List[str], completed: List[str]) -> List[str]:
    """Return commands that have not yet been completed."""
    done = set(completed)
    return [cmd for cmd in all_commands if cmd not in done]
