"""Hook command dependency ordering — ensures commands run after their declared deps."""

from __future__ import annotations

from typing import Dict, List, Optional


class DependencyError(Exception):
    """Raised when dependency resolution fails."""


def _build_graph(commands: List[dict]) -> Dict[str, List[str]]:
    """Return adjacency list: name -> list of names that depend on it."""
    names = {cmd.get("name") for cmd in commands if cmd.get("name")}
    graph: Dict[str, List[str]] = {name: [] for name in names}
    for cmd in commands:
        name = cmd.get("name")
        if not name:
            continue
        for dep in cmd.get("depends_on", []):
            if dep not in names:
                raise DependencyError(
                    f"Command '{name}' depends on unknown command '{dep}'."
                )
            graph[dep].append(name)
    return graph


def _topological_sort(commands: List[dict]) -> List[dict]:
    """Return commands sorted so each command appears after its dependencies."""
    by_name = {cmd["name"]: cmd for cmd in commands if cmd.get("name")}
    unnamed = [cmd for cmd in commands if not cmd.get("name")]

    in_degree: Dict[str, int] = {name: 0 for name in by_name}
    graph = _build_graph(list(by_name.values()))

    for name in by_name:
        cmd = by_name[name]
        for dep in cmd.get("depends_on", []):
            in_degree[name] += 1

    queue = [name for name, deg in in_degree.items() if deg == 0]
    queue.sort()  # deterministic order among independent nodes
    result: List[dict] = []

    while queue:
        current = queue.pop(0)
        result.append(by_name[current])
        for neighbour in sorted(graph[current]):
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    if len(result) != len(by_name):
        cycle_nodes = [n for n, d in in_degree.items() if d > 0]
        raise DependencyError(
            f"Circular dependency detected among commands: {cycle_nodes}"
        )

    return result + unnamed


def resolve_command_order(
    hook_config: dict,
    hook_name: Optional[str] = None,
) -> List[dict]:
    """Return the command list for *hook_name* sorted by dependency order.

    Commands without a ``name`` key are appended at the end unchanged.
    """
    commands: List[dict] = hook_config.get("commands", [])
    if not any(cmd.get("depends_on") for cmd in commands):
        return list(commands)  # fast-path: nothing to sort
    try:
        return _topological_sort(commands)
    except DependencyError as exc:
        prefix = f"[{hook_name}] " if hook_name else ""
        raise DependencyError(f"{prefix}{exc}") from exc
