"""Tests for hookrunner.checkpoint."""

import json
import pytest
from pathlib import Path

from hookrunner.checkpoint import (
    CheckpointError,
    save_checkpoint,
    load_checkpoint,
    clear_checkpoint,
    pending_commands,
)


@pytest.fixture()
def base(tmp_path):
    return tmp_path


def test_save_creates_file(base):
    path = save_checkpoint("pre-commit", ["cmd1", "cmd2"], base=base)
    assert path.exists()


def test_save_and_load_roundtrip(base):
    save_checkpoint("pre-commit", ["lint", "test"], base=base)
    result = load_checkpoint("pre-commit", base=base)
    assert result == ["lint", "test"]


def test_load_returns_none_when_missing(base):
    result = load_checkpoint("pre-push", base=base)
    assert result is None


def test_load_raises_on_corrupt_file(base):
    path = base / ".hookrunner_checkpoints" / "pre-commit.json"
    path.parent.mkdir(parents=True)
    path.write_text("not json{{{")
    with pytest.raises(CheckpointError, match="Could not read checkpoint"):
        load_checkpoint("pre-commit", base=base)


def test_load_raises_on_hook_mismatch(base):
    path = base / ".hookrunner_checkpoints" / "pre-commit.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"hook": "pre-push", "completed": [], "saved_at": 0}))
    with pytest.raises(CheckpointError, match="mismatch"):
        load_checkpoint("pre-commit", base=base)


def test_clear_removes_file(base):
    save_checkpoint("pre-commit", ["a"], base=base)
    removed = clear_checkpoint("pre-commit", base=base)
    assert removed is True
    assert load_checkpoint("pre-commit", base=base) is None


def test_clear_returns_false_when_missing(base):
    removed = clear_checkpoint("pre-commit", base=base)
    assert removed is False


def test_pending_commands_excludes_completed():
    all_cmds = ["lint", "typecheck", "test"]
    completed = ["lint"]
    assert pending_commands(all_cmds, completed) == ["typecheck", "test"]


def test_pending_commands_all_done():
    cmds = ["a", "b"]
    assert pending_commands(cmds, ["a", "b"]) == []


def test_pending_commands_none_done():
    cmds = ["x", "y"]
    assert pending_commands(cmds, []) == ["x", "y"]


def test_save_raises_on_unwritable_path(tmp_path):
    ro = tmp_path / "readonly"
    ro.mkdir()
    ro.chmod(0o444)
    try:
        with pytest.raises(CheckpointError, match="Could not save checkpoint"):
            save_checkpoint("pre-commit", ["cmd"], base=ro)
    finally:
        ro.chmod(0o755)
