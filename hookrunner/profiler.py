"""Hook execution profiler — tracks timing and performance of hook runs."""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CommandProfile:
    command: str
    start_time: float
    end_time: Optional[float] = None
    exit_code: Optional[int] = None

    @property
    def elapsed(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    @property
    def succeeded(self) -> Optional[bool]:
        if self.exit_code is None:
            return None
        return self.exit_code == 0


@dataclass
class HookProfile:
    hook_name: str
    start_time: float
    end_time: Optional[float] = None
    commands: List[CommandProfile] = field(default_factory=list)

    @property
    def elapsed(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    @property
    def total_commands(self) -> int:
        return len(self.commands)

    @property
    def failed_commands(self) -> int:
        return sum(1 for c in self.commands if c.succeeded is False)


class Profiler:
    """Collects timing data for hook and command execution."""

    def __init__(self) -> None:
        self._hooks: Dict[str, HookProfile] = {}
        self._active_hook: Optional[str] = None

    def start_hook(self, hook_name: str) -> None:
        self._hooks[hook_name] = HookProfile(hook_name=hook_name, start_time=time.monotonic())
        self._active_hook = hook_name

    def end_hook(self, hook_name: str) -> None:
        if hook_name in self._hooks:
            self._hooks[hook_name].end_time = time.monotonic()
        self._active_hook = None

    def start_command(self, command: str) -> CommandProfile:
        profile = CommandProfile(command=command, start_time=time.monotonic())
        if self._active_hook and self._active_hook in self._hooks:
            self._hooks[self._active_hook].commands.append(profile)
        return profile

    def end_command(self, profile: CommandProfile, exit_code: int) -> None:
        profile.end_time = time.monotonic()
        profile.exit_code = exit_code

    def get_hook_profile(self, hook_name: str) -> Optional[HookProfile]:
        return self._hooks.get(hook_name)

    def summary(self) -> List[HookProfile]:
        return list(self._hooks.values())
