"""Capture and buffer stdout/stderr from hook commands."""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import List, Optional


class OutputCaptureError(Exception):
    """Raised when output capture encounters an error."""


@dataclass
class CapturedOutput:
    """Holds captured stdout and stderr for a single command."""

    command: str
    stdout: str = ""
    stderr: str = ""
    returncode: Optional[int] = None

    @property
    def combined(self) -> str:
        """Return stdout and stderr interleaved as a single string."""
        parts = [p for p in (self.stdout, self.stderr) if p]
        return "\n".join(parts)

    @property
    def has_output(self) -> bool:
        return bool(self.stdout or self.stderr)


@dataclass
class HookOutput:
    """Aggregated output for all commands in a hook."""

    hook_name: str
    entries: List[CapturedOutput] = field(default_factory=list)

    def add(self, entry: CapturedOutput) -> None:
        self.entries.append(entry)

    def failed_entries(self) -> List[CapturedOutput]:
        return [e for e in self.entries if e.returncode not in (None, 0)]

    def format_summary(self, *, show_passing: bool = False) -> str:
        """Return a human-readable summary of captured output."""
        lines: List[str] = [f"[{self.hook_name}]"]
        for entry in self.entries:
            failed = entry.returncode not in (None, 0)
            if not failed and not show_passing:
                continue
            status = "FAIL" if failed else "PASS"
            lines.append(f"  [{status}] {entry.command}")
            if entry.stdout:
                for ln in entry.stdout.splitlines():
                    lines.append(f"    stdout: {ln}")
            if entry.stderr:
                for ln in entry.stderr.splitlines():
                    lines.append(f"    stderr: {ln}")
        return "\n".join(lines)


def capture_output(command: str, stdout: str, stderr: str, returncode: int) -> CapturedOutput:
    """Construct a CapturedOutput from raw subprocess results."""
    if not command:
        raise OutputCaptureError("command must not be empty")
    return CapturedOutput(
        command=command,
        stdout=stdout.rstrip("\n"),
        stderr=stderr.rstrip("\n"),
        returncode=returncode,
    )


def collect_hook_output(hook_name: str, captures: List[CapturedOutput]) -> HookOutput:
    """Bundle a list of CapturedOutput objects into a HookOutput."""
    if not hook_name:
        raise OutputCaptureError("hook_name must not be empty")
    ho = HookOutput(hook_name=hook_name)
    for c in captures:
        ho.add(c)
    return ho
