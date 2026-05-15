"""Audit module: records hook execution events to an append-only log file."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from hookrunner.notifier import HookEvent, Notifier


class AuditError(Exception):
    """Raised when the audit log cannot be written."""


DEFAULT_AUDIT_FILE = ".hookrunner_audit.jsonl"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _event_to_record(event: HookEvent) -> Dict[str, Any]:
    return {
        "timestamp": _now_iso(),
        "hook": event.hook_name,
        "event": event.event_type,
        "command": event.command,
        "return_code": event.return_code,
        "message": event.message,
    }


def append_audit_record(path: Path, event: HookEvent) -> None:
    """Append a JSON-lines record for *event* to *path*."""
    record = _event_to_record(event)
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError as exc:
        raise AuditError(f"Cannot write audit log {path}: {exc}") from exc


def load_audit_records(path: Path) -> list[Dict[str, Any]]:
    """Return all records stored in the JSONL audit file at *path*."""
    if not path.exists():
        return []
    records: list[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise AuditError(f"Corrupt audit record: {exc}") from exc
    return records


def attach_audit_listener(notifier: Notifier, path: Path | None = None) -> Path:
    """Subscribe an audit listener to all lifecycle events on *notifier*.

    Returns the resolved audit log path.
    """
    audit_path = path or Path(os.getcwd()) / DEFAULT_AUDIT_FILE

    def _listener(event: HookEvent) -> None:
        append_audit_record(audit_path, event)

    for event_type in ("start", "success", "failure", "command_start", "command_end"):
        notifier.subscribe(event_type, _listener)

    return audit_path
