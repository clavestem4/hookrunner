"""File watcher for auto-reloading hook configuration on changes."""

import os
import time
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 1.0  # seconds


class WatcherError(Exception):
    """Raised when the watcher encounters an unrecoverable error."""


def get_mtime(path: str) -> Optional[float]:
    """Return the modification time of a file, or None if it doesn't exist."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def watch_config(
    config_path: str,
    on_change: Callable[[str], None],
    stop_event=None,
    interval: float = CHECK_INTERVAL,
) -> None:
    """Watch a config file and invoke on_change when it is modified.

    Args:
        config_path: Absolute or relative path to the config file to watch.
        on_change: Callback invoked with the config path when a change is detected.
        stop_event: A threading.Event (or compatible) used to stop the loop.
                    If None the loop runs until interrupted.
        interval: Polling interval in seconds.

    Raises:
        WatcherError: If the config file does not exist at startup.
    """
    if not os.path.exists(config_path):
        raise WatcherError(f"Config file not found: {config_path}")

    last_mtime = get_mtime(config_path)
    logger.debug("Watching %s (mtime=%s)", config_path, last_mtime)

    while stop_event is None or not stop_event.is_set():
        time.sleep(interval)
        current_mtime = get_mtime(config_path)

        if current_mtime is None:
            logger.warning("Config file disappeared: %s", config_path)
            last_mtime = None
            continue

        if current_mtime != last_mtime:
            logger.info("Config changed: %s", config_path)
            last_mtime = current_mtime
            try:
                on_change(config_path)
            except Exception as exc:  # noqa: BLE001
                logger.error("on_change callback raised: %s", exc)
