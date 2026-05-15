"""Hook registry for tracking installed and available hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


class RegistryError(Exception):
    """Raised when registry operations fail."""


@dataclass
class HookEntry:
    """Represents a registered hook."""

    name: str
    script_path: Path
    commands: List[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "script_path": str(self.script_path),
            "commands": self.commands,
            "enabled": self.enabled,
        }


class HookRegistry:
    """In-memory registry of hooks known to hookrunner."""

    def __init__(self) -> None:
        self._hooks: Dict[str, HookEntry] = {}

    def register(self, entry: HookEntry) -> None:
        """Register or overwrite a hook entry."""
        self._hooks[entry.name] = entry

    def unregister(self, name: str) -> None:
        """Remove a hook by name. Raises RegistryError if not found."""
        if name not in self._hooks:
            raise RegistryError(f"Hook '{name}' is not registered.")
        del self._hooks[name]

    def get(self, name: str) -> Optional[HookEntry]:
        """Return a hook entry or None."""
        return self._hooks.get(name)

    def list_hooks(self) -> List[HookEntry]:
        """Return all registered hooks sorted by name."""
        return sorted(self._hooks.values(), key=lambda e: e.name)

    def enabled_hooks(self) -> List[HookEntry]:
        """Return only enabled hooks."""
        return [e for e in self.list_hooks() if e.enabled]

    def disable(self, name: str) -> None:
        """Disable a hook by name."""
        entry = self._hooks.get(name)
        if entry is None:
            raise RegistryError(f"Hook '{name}' is not registered.")
        entry.enabled = False

    def enable(self, name: str) -> None:
        """Enable a hook by name."""
        entry = self._hooks.get(name)
        if entry is None:
            raise RegistryError(f"Hook '{name}' is not registered.")
        entry.enabled = True

    def build_from_config(self, config: dict, hooks_dir: Path) -> None:
        """Populate registry from a loaded config dict."""
        hooks = config.get("hooks", {})
        for hook_name, commands in hooks.items():
            script_path = hooks_dir / hook_name
            entry = HookEntry(
                name=hook_name,
                script_path=script_path,
                commands=commands if isinstance(commands, list) else [],
            )
            self.register(entry)
