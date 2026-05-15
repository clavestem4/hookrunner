"""Tests for hookrunner.notifier."""

import pytest

from hookrunner.notifier import (
    HookEvent,
    Notifier,
    NotifierError,
    default_notifier,
)


# ---------------------------------------------------------------------------
# HookEvent
# ---------------------------------------------------------------------------

def test_hook_event_repr():
    ev = HookEvent(hook_name="pre-commit", event_type="start")
    assert "pre-commit" in repr(ev)
    assert "start" in repr(ev)


def test_hook_event_optional_fields_default_none():
    ev = HookEvent(hook_name="pre-push", event_type="success")
    assert ev.command is None
    assert ev.return_code is None
    assert ev.message is None


# ---------------------------------------------------------------------------
# Notifier.subscribe / listener_count
# ---------------------------------------------------------------------------

def test_subscribe_valid_event_type():
    n = Notifier()
    n.subscribe("start", lambda e: None)
    assert n.listener_count("start") == 1


def test_subscribe_invalid_event_type_raises():
    n = Notifier()
    with pytest.raises(NotifierError, match="Unknown event type"):
        n.subscribe("bogus", lambda e: None)


def test_multiple_listeners_same_event():
    n = Notifier()
    n.subscribe("failure", lambda e: None)
    n.subscribe("failure", lambda e: None)
    assert n.listener_count("failure") == 2


# ---------------------------------------------------------------------------
# Notifier.unsubscribe
# ---------------------------------------------------------------------------

def test_unsubscribe_removes_listener():
    n = Notifier()
    cb = lambda e: None  # noqa: E731
    n.subscribe("success", cb)
    n.unsubscribe("success", cb)
    assert n.listener_count("success") == 0


def test_unsubscribe_unknown_listener_is_silent():
    n = Notifier()
    # Should not raise even if listener was never registered.
    n.unsubscribe("start", lambda e: None)


# ---------------------------------------------------------------------------
# Notifier.notify
# ---------------------------------------------------------------------------

def test_notify_dispatches_to_correct_listeners():
    n = Notifier()
    received: list = []
    n.subscribe("start", lambda e: received.append(e))
    n.subscribe("failure", lambda e: received.append("wrong"))

    ev = HookEvent(hook_name="pre-commit", event_type="start")
    n.notify(ev)

    assert received == [ev]


def test_notify_no_listeners_does_nothing():
    n = Notifier()
    # Should not raise.
    n.notify(HookEvent(hook_name="pre-commit", event_type="success"))


def test_notify_listener_exception_raises_notifier_error():
    n = Notifier()

    def bad_listener(e):
        raise RuntimeError("boom")

    n.subscribe("command_end", bad_listener)
    ev = HookEvent(hook_name="pre-commit", event_type="command_end")
    with pytest.raises(NotifierError, match="boom"):
        n.notify(ev)


def test_notify_command_event_carries_metadata():
    n = Notifier()
    captured: list = []
    n.subscribe("command_end", captured.append)

    ev = HookEvent(
        hook_name="pre-push",
        event_type="command_end",
        command="pytest",
        return_code=0,
    )
    n.notify(ev)

    assert captured[0].command == "pytest"
    assert captured[0].return_code == 0


# ---------------------------------------------------------------------------
# Module-level default instance
# ---------------------------------------------------------------------------

def test_default_notifier_is_notifier_instance():
    assert isinstance(default_notifier, Notifier)
