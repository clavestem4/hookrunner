"""Lightweight metrics collector for hook execution statistics."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class MetricsError(Exception):
    """Raised when metrics operations fail."""


@dataclass
class CommandMetric:
    hook: str
    command: str
    duration: float
    exit_code: int
    timestamp: float = field(default_factory=time.time)

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


@dataclass
class HookMetric:
    hook: str
    total_duration: float
    command_count: int
    failure_count: int
    timestamp: float = field(default_factory=time.time)

    @property
    def passed(self) -> bool:
        return self.failure_count == 0


class MetricsCollector:
    def __init__(self) -> None:
        self._commands: List[CommandMetric] = []
        self._hooks: List[HookMetric] = []

    def record_command(self, hook: str, command: str, duration: float, exit_code: int) -> None:
        if not hook or not command:
            raise MetricsError("hook and command must be non-empty strings")
        self._commands.append(CommandMetric(hook=hook, command=command,
                                            duration=duration, exit_code=exit_code))

    def record_hook(self, hook: str, total_duration: float,
                    command_count: int, failure_count: int) -> None:
        if not hook:
            raise MetricsError("hook name must be a non-empty string")
        self._hooks.append(HookMetric(hook=hook, total_duration=total_duration,
                                      command_count=command_count, failure_count=failure_count))

    def commands_for_hook(self, hook: str) -> List[CommandMetric]:
        return [c for c in self._commands if c.hook == hook]

    def summary(self) -> Dict[str, object]:
        total = len(self._hooks)
        passed = sum(1 for h in self._hooks if h.passed)
        avg_duration: Optional[float] = None
        if self._hooks:
            avg_duration = sum(h.total_duration for h in self._hooks) / total
        return {
            "total_hooks": total,
            "passed": passed,
            "failed": total - passed,
            "avg_hook_duration": avg_duration,
        }

    def reset(self) -> None:
        self._commands.clear()
        self._hooks.clear()


_default_collector = MetricsCollector()


def get_collector() -> MetricsCollector:
    return _default_collector
