"""Pipeline: ordered stage execution with short-circuit on failure."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional


class PipelineError(Exception):
    """Raised when a pipeline stage fails and abort_on_failure is True."""


@dataclass
class Stage:
    name: str
    fn: Callable[[], bool]
    abort_on_failure: bool = True


@dataclass
class StageResult:
    name: str
    passed: bool
    skipped: bool = False
    error: Optional[Exception] = None


@dataclass
class PipelineResult:
    stages: List[StageResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.stages if not r.skipped)

    @property
    def failed_stages(self) -> List[StageResult]:
        return [r for r in self.stages if not r.passed and not r.skipped]


def run_pipeline(stages: List[Stage]) -> PipelineResult:
    """Execute stages in order. Abort on first failure if abort_on_failure is set."""
    result = PipelineResult()
    aborted = False

    for stage in stages:
        if aborted:
            result.stages.append(StageResult(name=stage.name, passed=True, skipped=True))
            continue

        try:
            passed = bool(stage.fn())
        except Exception as exc:  # noqa: BLE001
            result.stages.append(StageResult(name=stage.name, passed=False, error=exc))
            if stage.abort_on_failure:
                aborted = True
            continue

        sr = StageResult(name=stage.name, passed=passed)
        result.stages.append(sr)

        if not passed and stage.abort_on_failure:
            aborted = True

    return result


def build_pipeline_from_config(hook_name: str, config: dict) -> List[Stage]:
    """Build a list of Stage objects from a hook config dict."""
    hooks = config.get("hooks", {})
    hook_cfg = hooks.get(hook_name, {})
    commands = hook_cfg.get("commands", [])
    abort = hook_cfg.get("abort_on_failure", True)

    stages = []
    for cmd in commands:
        name = cmd if isinstance(cmd, str) else cmd.get("name", cmd.get("run", "unknown"))
        run = cmd if isinstance(cmd, str) else cmd.get("run", "")
        cmd_abort = abort if isinstance(cmd, str) else cmd.get("abort_on_failure", abort)

        import subprocess  # local import to keep module lightweight

        def make_fn(command: str) -> Callable[[], bool]:
            def fn() -> bool:
                r = subprocess.run(command, shell=True, capture_output=True)  # noqa: S602
                return r.returncode == 0
            return fn

        stages.append(Stage(name=name, fn=make_fn(run), abort_on_failure=cmd_abort))

    return stages
