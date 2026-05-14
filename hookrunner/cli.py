"""Command-line interface for hookrunner."""

import argparse
import sys
from pathlib import Path

from hookrunner.installer import InstallerError, find_git_hooks_dir, install_hooks, uninstall_hooks
from hookrunner.runner import HookRunnerError, run_hook


HOOK_TYPES = [
    "pre-commit",
    "pre-push",
    "commit-msg",
    "post-commit",
    "pre-rebase",
    "post-merge",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hookrunner",
        description="Lightweight Git hook manager.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # install
    install_parser = subparsers.add_parser("install", help="Install git hooks into .git/hooks")
    install_parser.add_argument(
        "--hooks",
        nargs="+",
        default=HOOK_TYPES,
        metavar="HOOK",
        help="Hook types to install (default: all supported hooks)",
    )

    # uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Remove installed git hooks")
    uninstall_parser.add_argument(
        "--hooks",
        nargs="+",
        default=HOOK_TYPES,
        metavar="HOOK",
        help="Hook types to uninstall (default: all supported hooks)",
    )

    # run
    run_parser = subparsers.add_parser("run", help="Manually run a specific hook")
    run_parser.add_argument("hook", metavar="HOOK", help="Hook type to run (e.g. pre-commit)")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "install":
            hooks_dir = find_git_hooks_dir(Path.cwd())
            install_hooks(hooks_dir, args.hooks)
            print(f"Installed {len(args.hooks)} hook(s) into {hooks_dir}")

        elif args.command == "uninstall":
            hooks_dir = find_git_hooks_dir(Path.cwd())
            removed = uninstall_hooks(hooks_dir, args.hooks)
            print(f"Uninstalled {removed} hook(s) from {hooks_dir}")

        elif args.command == "run":
            run_hook(args.hook, cwd=Path.cwd())

    except (InstallerError, HookRunnerError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
