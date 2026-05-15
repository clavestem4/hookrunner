"""Notifier module: emits hook lifecycle events to registered listeners."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List


class NotifierError(Exception):
    """Raised when a notifier operation fails."""


@dataclass
class HookEvent:
    """Represents a hook lifecycle event."""

    hook_name: str
    event_type: str  # 'start', 'success', 'failure', 'command_start', 'command_end'
    command: str | None = None
    return_code: int | None = None
    message: str | None = None

    def __repr__(self) -> str:
        return (
            f"HookEvent(hook={self.hook_name!r}, type={self.event_type!r}, "
            f"command={self.command!r}, rc={self.return_code})"
        )


Listener = Callable[[HookEvent], None]

_VALID_EVENT_TYPES = frozenset(
    {"start", "success", "failure", "command_start", "command_end"}
)


class Notifier:
    """Manages listeners and dispatches HookEvents to them."""

    def __init__(self) -> None:
        self._listeners: Dict[str, List[Listener]] = {}

    def subscribe(self, event_type: str, listener: Listener) -> None:
        """Register *listener* for *event_type*."""
        if event_type not in _VALID_EVENT_TYPES:
            raise NotifierError(
                f"Unknown event type {event_type!r}. "
                f"Valid types: {sorted(_VALID_EVENT_TYPES)}"
            )
        self._listeners.setdefault(event_type, []).append(listener)

    def unsubscribe(self, event_type: str, listener: Listener) -> None:
        """Remove *listener* from *event_type*. Silently ignores unknown listeners."""
        bucket = self._listeners.get(event_type, [])
        try:
            bucket.remove(listener)
        except ValueError:
            pass

    def notify(self, event: HookEvent) -> None:
        """Dispatch *event* to all registered listeners for its type."""
        for listener in list(self._listeners.get(event.event_type, [])):
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001
                raise NotifierError(
                    f"Listener {listener!r} raised an error: {exc}"
                ) from exc

    def listener_count(self, event_type: str) -> int:
        """Return the number of listeners registered for *event_type*."""
        return len(self._listeners.get(event_type, []))


# Module-level default notifier instance.
default_notifier: Notifier = Notifier()
