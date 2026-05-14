"""Output formatting utilities for hookrunner."""

import sys
from enum import Enum
from typing import Optional


class Color(str, Enum):
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"


def _supports_color(stream=None) -> bool:
    """Return True if the given stream supports ANSI color codes."""
    stream = stream or sys.stdout
    return hasattr(stream, "isatty") and stream.isatty()


def colorize(text: str, color: Color, stream=None) -> str:
    """Wrap text in ANSI color codes if the stream supports color."""
    if _supports_color(stream):
        return f"{color.value}{text}{Color.RESET.value}"
    return text


def format_hook_header(hook_name: str, stream=None) -> str:
    """Format a hook section header."""
    label = f"[hookrunner] Running hook: {hook_name}"
    return colorize(label, Color.BOLD, stream)


def format_command_start(command: str, stream=None) -> str:
    """Format a command start line."""
    label = f"  → {command}"
    return colorize(label, Color.CYAN, stream)


def format_success(message: Optional[str] = None, stream=None) -> str:
    """Format a success message."""
    text = message or "All commands passed."
    return colorize(f"  ✔ {text}", Color.GREEN, stream)


def format_failure(message: str, stream=None) -> str:
    """Format a failure message."""
    return colorize(f"  ✘ {message}", Color.RED, stream)


def format_warning(message: str, stream=None) -> str:
    """Format a warning message."""
    return colorize(f"  ⚠ {message}", Color.YELLOW, stream)


def print_hook_summary(hook_name: str, passed: bool, stream=None) -> None:
    """Print a final summary line for a hook run."""
    stream = stream or sys.stdout
    if passed:
        line = format_success(f"Hook '{hook_name}' passed.", stream)
    else:
        line = format_failure(f"Hook '{hook_name}' failed.", stream)
    print(line, file=stream)
