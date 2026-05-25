"""Structured logging helpers for hookrunner."""

import logging
import sys
from typing import Optional

LOG_FORMAT = "%(levelname)s %(name)s: %(message)s"
_loggers: dict = {}


def get_logger(name: str = "hookrunner") -> logging.Logger:
    """Return a named logger, creating it once with consistent settings."""
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
    logger.propagate = False
    _loggers[name] = logger
    return logger


def configure_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Set the root hookrunner logger level based on CLI flags."""
    logger = get_logger()
    if quiet:
        logger.setLevel(logging.ERROR)
    elif verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


def log_hook_start(hook_name: str) -> None:
    get_logger().info("Starting hook: %s", hook_name)


def log_command(command: str) -> None:
    get_logger().debug("Executing command: %s", command)


def log_command_success(command: str, return_code: int) -> None:
    get_logger().debug("Command succeeded (rc=%d): %s", return_code, command)


def log_command_failure(command: str, return_code: int, stderr: Optional[str] = None) -> None:
    logger = get_logger()
    logger.error("Command failed (rc=%d): %s", return_code, command)
    if stderr:
        logger.error("stderr: %s", stderr.strip())


def log_hook_complete(hook_name: str, passed: bool) -> None:
    logger = get_logger()
    if passed:
        logger.info("Hook '%s' completed successfully.", hook_name)
    else:
        logger.error("Hook '%s' completed with errors.", hook_name)


def log_skipped_hook(hook_name: str, reason: Optional[str] = None) -> None:
    """Log that a hook was skipped, with an optional reason.

    Args:
        hook_name: The name of the hook that was skipped.
        reason: An optional human-readable explanation for why the hook was skipped.
    """
    logger = get_logger()
    if reason:
        logger.info("Skipping hook '%s': %s", hook_name, reason)
    else:
        logger.info("Skipping hook '%s'.", hook_name)
