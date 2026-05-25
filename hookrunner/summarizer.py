"""hookrunner.summarizer – produce a human-readable run summary.

Builds a structured summary from a HookProfile (profiler) and the list
of ValidationWarning objects (validator) collected during a hook run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from hookrunner.profiler import HookProfile
from hookrunner.validator import ValidationWarning


class SummarizerError(Exception):
    """Raised when summary generation fails."""


@dataclass
class CommandSummary:
    name: str
    elapsed: Optional[float]
    succeeded: Optional[bool]
    warnings: List[str] = field(default_factory=list)


@dataclass
class HookSummary:
    hook_name: str
    total_elapsed: Optional[float]
    passed: bool
    commands: List[CommandSummary] = field(default_factory=list)
    warning_count: int = 0

    def as_dict(self) -> dict:
        return {
            "hook": self.hook_name,
            "passed": self.passed,
            "elapsed": self.total_elapsed,
            "warning_count": self.warning_count,
            "commands": [
                {
                    "name": c.name,
                    "elapsed": c.elapsed,
                    "succeeded": c.succeeded,
                    "warnings": c.warnings,
                }
                for c in self.commands
            ],
        }


def build_summary(
    profile: HookProfile,
    warnings: Optional[List[ValidationWarning]] = None,
) -> HookSummary:
    """Combine profiling data and validation warnings into a HookSummary."""
    if profile is None:
        raise SummarizerError("profile must not be None")

    warnings = warnings or []

    # Index warnings by command name for quick lookup
    warn_index: dict[str, List[str]] = {}
    for w in warnings:
        warn_index.setdefault(w.command, []).append(str(w))

    cmd_summaries = [
        CommandSummary(
            name=cp.name,
            elapsed=cp.elapsed,
            succeeded=cp.succeeded,
            warnings=warn_index.get(cp.name, []),
        )
        for cp in profile.commands
    ]

    return HookSummary(
        hook_name=profile.hook_name,
        total_elapsed=profile.elapsed,
        passed=profile.passed,
        commands=cmd_summaries,
        warning_count=len(warnings),
    )


def format_summary(summary: HookSummary) -> str:
    """Return a plain-text representation of a HookSummary."""
    status = "PASSED" if summary.passed else "FAILED"
    elapsed = f"{summary.total_elapsed:.3f}s" if summary.total_elapsed is not None else "n/a"
    lines = [f"Hook '{summary.hook_name}': {status} in {elapsed}"]
    for cmd in summary.commands:
        icon = "✓" if cmd.succeeded else ("✗" if cmd.succeeded is False else "?")
        cmd_elapsed = f"{cmd.elapsed:.3f}s" if cmd.elapsed is not None else "n/a"
        lines.append(f"  {icon} {cmd.name} ({cmd_elapsed})")
        for w in cmd.warnings:
            lines.append(f"    ⚠ {w}")
    if summary.warning_count:
        lines.append(f"  {summary.warning_count} warning(s) total")
    return "\n".join(lines)
