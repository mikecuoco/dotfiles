"""dotfiles CLI — cross-platform dotfiles manager."""
from __future__ import annotations

import argparse
import sys


def _add_dry_run(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making any changes",
    )


def _add_skills_args(parser: argparse.ArgumentParser, verb: str) -> None:
    """Add the flags shared by ``skills install`` and ``skills update``."""
    parser.add_argument(
        "--with",
        dest="extra_groups",
        action="append",
        default=[],
        metavar="GROUP",
        help=f"Additional skill group to {verb}: spatial | genomics | all (repeatable)",
    )
    parser.add_argument(
        "--allow-large",
        action="store_true",
        help="Allow the 561-skill 'all' group despite discovery-context costs",
    )
    _add_dry_run(parser)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dotfiles",
        description="Cross-platform dotfiles manager (https://github.com/mikecuoco/dotfiles)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_version()}",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── install ──────────────────────────────────────────────────────────────
    p_install = sub.add_parser(
        "install",
        help="Install dotfiles for the active (or specified) profile",
    )
    p_install.add_argument(
        "--profile", "-p",
        metavar="PROFILE",
        help="Profile to install: macos | linux | cluster | codeocean | codespace "
             "(auto-detected if omitted)",
    )
    _add_dry_run(p_install)
    p_install.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress routine install output; errors are still shown",
    )
    p_install.add_argument(
        "--home",
        metavar="DIR",
        help="Override home directory (useful for testing)",
    )
    p_install.add_argument(
        "--claude-home",
        metavar="DIR",
        help="Override base directory for .claude/ files and skills "
             "(default: /root/capsule on Code Ocean when that path exists, "
             "otherwise HOME)",
    )

    # ── update ───────────────────────────────────────────────────────────────
    p_update = sub.add_parser(
        "update",
        help="Upgrade dotfiles from GitHub and apply the active profile",
    )
    p_update.add_argument(
        "--profile", "-p",
        metavar="PROFILE",
        help="Profile to apply after updating (auto-detected if omitted)",
    )
    p_update.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show the update and install commands without running them",
    )
    p_update.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress routine output while applying dotfiles",
    )

    # ── doctor ───────────────────────────────────────────────────────────────
    p_doctor = sub.add_parser(
        "doctor",
        help="Check dotfiles installation health",
    )
    p_doctor.add_argument(
        "--json",
        action="store_true",
        help="Emit results as JSON",
    )

    # ── auth ─────────────────────────────────────────────────────────────────
    sub.add_parser(
        "auth",
        help="Check authentication status (Anthropic, GitHub, AWS, Mem0)",
    )

    # ── status ───────────────────────────────────────────────────────────────
    sub.add_parser(
        "status",
        help="Show currently installed dotfiles state",
    )

    # ── profiles ─────────────────────────────────────────────────────────────
    sub.add_parser(
        "profiles",
        help="List available profiles",
    )

    # ── agent-stats / claude-stats ──────────────────────────────────────────
    sub.add_parser(
        "agent-stats",
        help="Report Claude and Codex instruction context budgets",
    )
    sub.add_parser(
        "claude-stats",
        help="Alias for agent-stats",
    )

    # ── skills ───────────────────────────────────────────────────────────────
    p_skills = sub.add_parser(
        "skills",
        help="Manage bundled and GPTomics skills for Claude Code and Codex",
    )
    skills_sub = p_skills.add_subparsers(
        dest="skills_command",
        metavar="SUBCOMMAND",
    )
    skills_sub.required = True
    # Let the skills handler raise usage errors against this subparser, so the
    # printed "usage:" line stays scoped to `dotfiles skills`.
    p_skills.set_defaults(group_parser=p_skills)

    _add_skills_args(skills_sub.add_parser(
        "install",
        help="Install skills into ~/.claude/skills/ and ~/.agents/skills/",
    ), "install")
    _add_skills_args(skills_sub.add_parser(
        "update",
        help="Refresh bundled skills and selected GPTomics groups",
    ), "update")

    skills_sub.add_parser(
        "status",
        help="Show dotfiles-managed and GPTomics skills for Claude Code and Codex",
    )

    # ── project memory ──────────────────────────────────────────────────────
    p_memory = sub.add_parser(
        "memory",
        help="Manage shared project memories under .agents/memory/",
    )
    memory_sub = p_memory.add_subparsers(
        dest="memory_command",
        metavar="SUBCOMMAND",
    )
    memory_sub.required = True

    memory_commands = {
        "init": memory_sub.add_parser(
            "init", help="Create the project memory directory safely"
        ),
        "list": memory_sub.add_parser(
            "list", help="List memory filenames and titles"
        ),
        "check": memory_sub.add_parser(
            "check", help="Validate project memory files and Git ignore behavior"
        ),
        "migrate": memory_sub.add_parser(
            "migrate", help="Review or copy safe files from obsolete memory paths"
        ),
    }
    for memory_parser in memory_commands.values():
        memory_parser.add_argument(
            "--repo",
            metavar="DIR",
            default=".",
            help="Repository path (default: current directory)",
        )
    for name in ("list", "check"):
        memory_commands[name].add_argument(
            "--json", action="store_true", help="Emit results as JSON"
        )
    memory_commands["migrate"].add_argument(
        "--apply",
        action="store_true",
        help="Copy safe candidates; never deletes legacy files",
    )

    # ── claude ───────────────────────────────────────────────────────────────
    p_claude = sub.add_parser(
        "claude",
        help="Manage Claude Code plugins and MCP server integrations",
    )
    claude_sub = p_claude.add_subparsers(
        dest="claude_command",
        metavar="SUBCOMMAND",
    )
    claude_sub.required = True

    p_setup = claude_sub.add_parser(
        "setup",
        help="Idempotently install plugins and MCP servers",
    )
    p_setup.add_argument(
        "--with",
        dest="extra_groups",
        action="append",
        default=[],
        metavar="GROUP",
        help="Additional plugin group to install, e.g. bioinformatics (repeatable)",
    )
    _add_dry_run(p_setup)

    return parser


# ── Command handlers ─────────────────────────────────────────────────────────
# Imports stay inside the handlers: only one command runs per invocation, and
# deferring them keeps CLI startup fast.

def _cmd_install(args: argparse.Namespace) -> int:
    from pathlib import Path
    from .install import run_install
    ok = run_install(
        profile=args.profile,
        dry_run=args.dry_run,
        home=Path(args.home) if args.home else None,
        quiet=args.quiet,
    )
    return 0 if ok else 1


def _cmd_update(args: argparse.Namespace) -> int:
    from .update import run_update
    return run_update(profile=args.profile, dry_run=args.dry_run, quiet=args.quiet)


def _cmd_doctor(args: argparse.Namespace) -> int:
    from .doctor import run_doctor
    return run_doctor(as_json=args.json)


def _cmd_auth(args: argparse.Namespace) -> int:
    from .auth import run_auth
    return run_auth()


def _cmd_status(args: argparse.Namespace) -> int:
    from .install import run_status
    return run_status()


def _cmd_profiles(args: argparse.Namespace) -> None:
    _list_profiles()
    return None


def _cmd_agent_stats(args: argparse.Namespace) -> int:
    from .claude_stats import run_agent_stats
    return run_agent_stats()


def _cmd_skills(args: argparse.Namespace):
    from collections import Counter
    from pathlib import Path
    from . import RESOURCES_DIR
    from .agent_skills import run_skills_setup, check_skill_statuses

    target_dir = Path.home() / ".claude" / "skills"
    codex_target_dir = Path.home() / ".agents" / "skills"

    if args.skills_command in {"install", "update"}:
        groups = ["default"] + (args.extra_groups or [])
        if "all" in groups and not args.allow_large:
            args.group_parser.error("the 'all' group requires --allow-large")
        statuses = run_skills_setup(
            resources_dir=RESOURCES_DIR,
            groups=groups,
            cache_dir=Path.home() / ".local" / "share" / "dotfiles" / "bioskills",
            target_dir=target_dir,
            codex_target_dir=codex_target_dir,
            dry_run=args.dry_run,
            update=args.skills_command == "update",
        )
        failed = [s for s in statuses if not s.installed and not args.dry_run]
        return 1 if failed else 0

    if args.skills_command == "status":
        found = False
        for agent, agent_target in (
            ("Claude Code", target_dir),
            ("Codex", codex_target_dir),
        ):
            statuses = check_skill_statuses(agent_target)
            if not statuses:
                print(f"  – no managed {agent} skills installed in {agent_target}")
                continue
            found = True
            print(f"  {len(statuses)} {agent} skill(s) found in {agent_target}")
            for cat, count in sorted(Counter(s.category for s in statuses).items()):
                print(f"    {cat:<30} {count}")
        if not found:
            print("    Run: dotfiles skills install")
        return 0

    return None


def _cmd_memory(args: argparse.Namespace):
    from pathlib import Path
    from .project_memory import (
        run_memory_check,
        run_memory_init,
        run_memory_list,
        run_memory_migrate,
    )

    repo = Path(args.repo)
    if args.memory_command == "init":
        return run_memory_init(repo)
    if args.memory_command == "list":
        return run_memory_list(repo, as_json=args.json)
    if args.memory_command == "check":
        return run_memory_check(repo, as_json=args.json)
    if args.memory_command == "migrate":
        return run_memory_migrate(repo, apply=args.apply)
    return None


def _cmd_claude(args: argparse.Namespace) -> int:
    from . import RESOURCES_DIR
    from .claude_plugins import run_claude_setup
    statuses = run_claude_setup(
        resources_dir=RESOURCES_DIR,
        groups=["default"] + (args.extra_groups or []),
        dry_run=args.dry_run,
    )
    # Non-zero exit if any integration failed outright (not auth-only)
    failed = [s for s in statuses if not s.installed and not args.dry_run
              and not s.message.startswith("command not found")]
    return 1 if failed else 0


_HANDLERS = {
    "install": _cmd_install,
    "update": _cmd_update,
    "doctor": _cmd_doctor,
    "auth": _cmd_auth,
    "status": _cmd_status,
    "profiles": _cmd_profiles,
    "agent-stats": _cmd_agent_stats,
    "claude-stats": _cmd_agent_stats,
    "skills": _cmd_skills,
    "memory": _cmd_memory,
    "claude": _cmd_claude,
}


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    code = _HANDLERS[args.command](args)
    if code is not None:
        sys.exit(code)


def _list_profiles() -> None:
    from . import RESOURCES_DIR
    from .profiles import load_profiles
    profiles = load_profiles(RESOURCES_DIR)
    print("Available profiles:\n")
    for name, p in sorted(profiles.items()):
        inherits = f"  (inherits: {', '.join(p.inherits)})" if p.inherits else ""
        print(f"  {name:<12} {p.description}{inherits}")


def _version() -> str:
    from importlib.metadata import version, PackageNotFoundError
    try:
        return version("mike-dotfiles")
    except PackageNotFoundError:
        return "dev"
