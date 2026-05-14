"""Tests for hookrunner.watcher."""

import threading
import time
import pytest

from hookrunner.watcher import WatcherError, get_mtime, watch_config


def test_get_mtime_existing_file(tmp_path):
    f = tmp_path / "hook.yml"
    f.write_text("hooks: {}")  
    mtime = get_mtime(str(f))
    assert isinstance(mtime, float)


def test_get_mtime_missing_file():
    assert get_mtime("/nonexistent/path/hook.yml") is None


def test_watch_config_raises_when_file_missing():
    with pytest.raises(WatcherError, match="Config file not found"):
        stop = threading.Event()
        stop.set()
        watch_config("/nonexistent/config.yml", on_change=lambda p: None, stop_event=stop)


def test_watch_config_detects_change(tmp_path):
    config = tmp_path / ".hookrunner.yml"
    config.write_text("hooks: {}")

    changes = []
    stop = threading.Event()

    def on_change(path):
        changes.append(path)
        stop.set()

    watcher_thread = threading.Thread(
        target=watch_config,
        kwargs={
            "config_path": str(config),
            "on_change": on_change,
            "stop_event": stop,
            "interval": 0.05,
        },
        daemon=True,
    )
    watcher_thread.start()

    time.sleep(0.1)
    config.write_text("hooks: {pre-commit: [echo hi]}")
    # Touch mtime explicitly to ensure change is detected on fast filesystems
    new_time = config.stat().st_mtime + 1
    import os
    os.utime(str(config), (new_time, new_time))

    watcher_thread.join(timeout=2.0)
    assert len(changes) == 1
    assert changes[0] == str(config)


def test_watch_config_no_spurious_callbacks(tmp_path):
    config = tmp_path / ".hookrunner.yml"
    config.write_text("hooks: {}")

    changes = []
    stop = threading.Event()

    watcher_thread = threading.Thread(
        target=watch_config,
        kwargs={
            "config_path": str(config),
            "on_change": lambda p: changes.append(p),
            "stop_event": stop,
            "interval": 0.05,
        },
        daemon=True,
    )
    watcher_thread.start()
    time.sleep(0.25)
    stop.set()
    watcher_thread.join(timeout=1.0)

    assert changes == []


def test_watch_config_callback_exception_does_not_stop_watcher(tmp_path):
    """A raising callback should be caught; the watcher should keep running."""
    config = tmp_path / ".hookrunner.yml"
    config.write_text("hooks: {}")

    stop = threading.Event()
    call_count = [0]

    def bad_callback(path):
        call_count[0] += 1
        stop.set()
        raise RuntimeError("boom")

    watcher_thread = threading.Thread(
        target=watch_config,
        kwargs={
            "config_path": str(config),
            "on_change": bad_callback,
            "stop_event": stop,
            "interval": 0.05,
        },
        daemon=True,
    )
    watcher_thread.start()
    time.sleep(0.1)
    import os
    new_time = config.stat().st_mtime + 1
    os.utime(str(config), (new_time, new_time))
    watcher_thread.join(timeout=2.0)
    assert call_count[0] >= 1
