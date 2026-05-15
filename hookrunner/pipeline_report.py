"""Human-readable reporting for PipelineResult."""

from __future__ import annotations

from typing import Optional

from hookrunner.formatter import Color, colorize
from hookrunner.pipeline import PipelineResult, StageResult

_PASS_ICON = "✔"
_FAIL_ICON = "✘"
_SKIP_ICON = "◌"


def _stage_line(result: StageResult, use_color: bool) -> str:
    if result.skipped:
        icon = colorize(_SKIP_ICON, Color.YELLOW, use_color)
        label = colorize("SKIPPED", Color.YELLOW, use_color)
    elif result.passed:
        icon = colorize(_PASS_ICON, Color.GREEN, use_color)
        label = colorize("PASS", Color.GREEN, use_color)
    else:
        icon = colorize(_FAIL_ICON, Color.RED, use_color)
        label = colorize("FAIL", Color.RED, use_color)

    suffix = f"  [{result.error}]" if result.error else ""
    return f"  {icon}  {result.name} — {label}{suffix}"


def format_pipeline_report(
    hook_name: str,
    result: PipelineResult,
    use_color: bool = True,
) -> str:
    """Return a multi-line string summarising the pipeline result."""
    lines = []
    header_color = Color.CYAN
    lines.append(colorize(f"Pipeline: {hook_name}", header_color, use_color))
    lines.append(colorize("-" * 40, header_color, use_color))

    for stage_result in result.stages:
        lines.append(_stage_line(stage_result, use_color))

    lines.append(colorize("-" * 40, header_color, use_color))
    if result.passed:
        summary = colorize("All stages passed.", Color.GREEN, use_color)
    else:
        failed = len(result.failed_stages)
        summary = colorize(f"{failed} stage(s) failed.", Color.RED, use_color)
    lines.append(summary)
    return "\n".join(lines)


def print_pipeline_report(
    hook_name: str,
    result: PipelineResult,
    use_color: bool = True,
) -> None:
    """Print the pipeline report to stdout."""
    print(format_pipeline_report(hook_name, result, use_color=use_color))
