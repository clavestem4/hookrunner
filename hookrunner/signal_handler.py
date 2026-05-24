"""Signal handling for hookrunner.

Provides graceful shutdown support when the process receives SIGINT or SIGTERM
during hook execution.  Consumers can register cleanup callbacks that will be
invoked before the process exits, ensuring temporary files, lock files, and
semaphores are released even when the user hits Ctrl-C.
"""

import os
import signal
import logging
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SignalHandlerError(Exception):
    """Raised when signal handler registration or cleanup fails."""


# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_cleanup_callbacks: List[Callable[[], None]] = []
_original_handlers: dict = {}
_installed: bool = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def register_cleanup(callback: Callable[[], None]) -> None:
    """Register a zero-argument callable to be called on graceful shutdown.

    Callbacks are invoked in LIFO order (most recently registered first),
    mirroring the behaviour of :func:`atexit.register`.

    Args:
        callback: A callable that takes no arguments.  Any exception raised
            inside the callback is logged and suppressed so that remaining
            callbacks still run.
    """
    if not callable(callback):
        raise SignalHandlerError("callback must be callable")
    _cleanup_callbacks.append(callback)


def unregister_cleanup(callback: Callable[[], None]) -> bool:
    """Remove a previously registered cleanup callback.

    Args:
        callback: The exact callable object that was passed to
            :func:`register_cleanup`.

    Returns:
        ``True`` if the callback was found and removed, ``False`` otherwise.
    """
    try:
        _cleanup_callbacks.remove(callback)
        return True
    except ValueError:
        return False


def run_cleanups() -> None:
    """Invoke all registered cleanup callbacks in LIFO order.

    Exceptions raised by individual callbacks are logged at WARNING level and
    do not prevent subsequent callbacks from running.
    """
    for cb in reversed(_cleanup_callbacks):
        try:
            cb()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cleanup callback %r raised: %s", cb, exc)


def install(
    signals: Optional[List[int]] = None,
    exit_code: int = 130,
) -> None:
    """Install signal handlers for graceful shutdown.

    Installs handlers for *signals* (default: ``[SIGINT, SIGTERM]``) that run
    all registered cleanup callbacks and then exit with *exit_code*.

    Calling this function more than once is a no-op; the handlers are only
    installed once per process.

    Args:
        signals: List of signal numbers to handle.  Defaults to
            ``[signal.SIGINT, signal.SIGTERM]``.
        exit_code: The exit code passed to :func:`os._exit` after cleanup.
            Defaults to 130 (the conventional code for Ctrl-C termination).
    """
    global _installed  # noqa: PLW0603

    if _installed:
        return

    if signals is None:
        signals = [signal.SIGINT, signal.SIGTERM]

    def _handler(signum: int, frame) -> None:  # noqa: ANN001
        sig_name = signal.Signals(signum).name
        logger.info("Received %s — running cleanup callbacks", sig_name)
        run_cleanups()
        os._exit(exit_code)  # noqa: SLF001

    for sig in signals:
        try:
            _original_handlers[sig] = signal.signal(sig, _handler)
        except (OSError, ValueError) as exc:
            raise SignalHandlerError(
                f"Failed to install handler for signal {sig}: {exc}"
            ) from exc

    _installed = True
    logger.debug("Signal handlers installed for: %s", signals)


def uninstall() -> None:
    """Restore original signal handlers and clear registered callbacks.

    Intended primarily for use in tests so that a clean state can be
    established between test cases.
    """
    global _installed  # noqa: PLW0603

    for sig, original in _original_handlers.items():
        try:
            signal.signal(sig, original)
        except (OSError, ValueError) as exc:
            logger.warning("Could not restore handler for signal %s: %s", sig, exc)

    _original_handlers.clear()
    _cleanup_callbacks.clear()
    _installed = False
