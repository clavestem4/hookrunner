"""Tests for hookrunner.audit."""

import json
from pathlib import Path

import pytest

from hookrunner.audit import (
    AuditError,
    DEFAULT_AUDIT_FILE,
    append_audit_record,
    attach_audit_listener,
    load_audit_records,
)
from hookrunner.notifier import HookEvent, Notifier


# ---------------------------------------------------------------------------
# append_audit_record
# ---------------------------------------------------------------------------

def test_append_creates_file(tmp_path):
    log = tmp_path / "audit.jsonl"
    ev = HookEvent(hook_name="pre-commit", event_type="start")
    append_audit_record(log, ev)
    assert log.exists()


def test_append_writes_valid_json(tmp_path):
    log = tmp_path / "audit.jsonl"
    ev = HookEvent(hook_name="pre-commit", event_type="success", command="pytest", return_code=0)
    append_audit_record(log, ev)
    record = json.loads(log.read_text())
    assert record["hook"] == "pre-commit"
    assert record["event"] == "success"
    assert record["command"] == "pytest"
    assert record["return_code"] == 0
    assert "timestamp" in record


def test_append_multiple_records(tmp_path):
    log = tmp_path / "audit.jsonl"
    for event_type in ("start", "success"):
        ev = HookEvent(hook_name="pre-push", event_type=event_type)
        append_audit_record(log, ev)
    lines = [l for l in log.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


def test_append_raises_on_bad_path():
    bad = Path("/no/such/directory/audit.jsonl")
    ev = HookEvent(hook_name="pre-commit", event_type="start")
    with pytest.raises(AuditError, match="Cannot write audit log"):
        append_audit_record(bad, ev)


# ---------------------------------------------------------------------------
# load_audit_records
# ---------------------------------------------------------------------------

def test_load_returns_empty_list_when_missing(tmp_path):
    records = load_audit_records(tmp_path / "nonexistent.jsonl")
    assert records == []


def test_load_returns_all_records(tmp_path):
    log = tmp_path / "audit.jsonl"
    for event_type in ("start", "command_start", "command_end", "success"):
        append_audit_record(log, HookEvent(hook_name="pre-commit", event_type=event_type))
    records = load_audit_records(log)
    assert len(records) == 4
    assert records[0]["event"] == "start"


def test_load_raises_on_corrupt_record(tmp_path):
    log = tmp_path / "audit.jsonl"
    log.write_text("not-valid-json\n")
    with pytest.raises(AuditError, match="Corrupt audit record"):
        load_audit_records(log)


# ---------------------------------------------------------------------------
# attach_audit_listener
# ---------------------------------------------------------------------------

def test_attach_returns_path(tmp_path):
    n = Notifier()
    returned = attach_audit_listener(n, path=tmp_path / "test.jsonl")
    assert returned == tmp_path / "test.jsonl"


def test_attach_uses_default_filename_when_no_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    n = Notifier()
    returned = attach_audit_listener(n)
    assert returned.name == DEFAULT_AUDIT_FILE


def test_attach_subscribes_to_all_event_types(tmp_path):
    log = tmp_path / "audit.jsonl"
    n = Notifier()
    attach_audit_listener(n, path=log)

    for event_type in ("start", "success", "failure", "command_start", "command_end"):
        n.notify(HookEvent(hook_name="pre-commit", event_type=event_type))

    records = load_audit_records(log)
    event_types_logged = {r["event"] for r in records}
    assert event_types_logged == {"start", "success", "failure", "command_start", "command_end"}
