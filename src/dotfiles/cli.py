"""dotfiles CLI — cross-platform dotfiles manager."""
from __future__ import annotations

import argparse
import sys


def main() -> None:
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
    p_install.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making any changes",
    )
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

    p_skills_install = skills_sub.add_parser(
        "install",
        help="Install skills into ~/.claude/skills/ and ~/.agents/skills/",
    )
    p_skills_install.add_argument(
        "--with",
        dest="extra_groups",
        action="append",
        default=[],
        metavar="GROUP",
        help="Additional skill group to install: spatial | genomics | all (repeatable)",
    )
    p_skills_install.add_argument(
        "--allow-large",
        action="store_true",
        help="Allow the 561-skill 'all' group despite discovery-context costs",
    )
    p_skills_install.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making any changes",
    )

    p_skills_update = skills_sub.add_parser(
        "update",
        help="Refresh bundled skills and selected GPTomics groups",
    )
    p_skills_update.add_argument(
        "--with",
        dest="extra_groups",
        action="append",
        default=[],
        metavar="GROUP",
        help="Additional skill group to update: spatial | genomics | all (repeatable)",
    )
    p_skills_update.add_argument(
        "--allow-large",
        action="store_true",
        help="Allow the 561-skill 'all' group despite discovery-context costs",
    )
    p_skills_update.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making any changes",
    )

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
    p_setup.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making any changes",
    )

    args = parser.parse_args()

    if args.command == "install":
        from pathlib import Path
        from .install import run_install
        home = Path(args.home) if args.home else None
        ok = run_install(
            profile=args.profile,
            dry_run=args.dry_run,
            home=home,
            quiet=args.quiet,
        )
        sys.exit(0 if ok else 1)
    elif args.command == "update":
        from .update import run_update
        sys.exit(run_update(
            profile=args.profile,
            dry_run=args.dry_run,
            quiet=args.quiet,
        ))
    elif args.command == "doctor":
        from .doctor import run_doctor
        sys.exit(run_doctor(as_json=args.json))
    elif args.command == "auth":
        from .auth import run_auth
        sys.exit(run_auth())
    elif args.command == "status":
        from .install import run_status
        sys.exit(run_status())
    elif args.command == "profiles":
        _list_profiles()
    elif args.command in ("agent-stats", "claude-stats"):
        from .claude_stats import run_agent_stats
        sys.exit(run_agent_stats())
    elif args.command == "skills":
        from pathlib import Path
        from . import RESOURCES_DIR
        from .agent_skills import run_skills_setup, check_skill_statuses

        cache_dir = Path.home() / ".local" / "share" / "dotfiles" / "bioskills"
        target_dir = Path.home() / ".claude" / "skills"
        codex_target_dir = Path.home() / ".agents" / "skills"

        if args.skills_command in {"install", "update"}:
            groups = ["default"] + (args.extra_groups or [])
            if "all" in groups and not args.allow_large:
                p_skills.error("the 'all' group requires --allow-large")
            statuses = run_skills_setup(
                resources_dir=RESOURCES_DIR,
                groups=groups,
                cache_dir=cache_dir,
                target_dir=target_dir,
                codex_target_dir=codex_target_dir,
                dry_run=args.dry_run,
                update=args.skills_command == "update",
            )
            failed = [s for s in statuses if not s.installed and not args.dry_run]
            sys.exit(1 if failed else 0)
        elif args.skills_command == "status":
            from collections import Counter
            found = False
            for agent, agent_target in (
                ("Claude Code", target_dir),
                ("Codex", codex_target_dir),
            ):
                statuses = check_skill_statuses(agent_target)
                total = len(statuses)
                if total == 0:
                    print(f"  – no managed {agent} skills installed in {agent_target}")
                    continue
                found = True
                by_cat = Counter(s.category for s in statuses)
                print(f"  {total} {agent} skill(s) found in {agent_target}")
                for cat, count in sorted(by_cat.items()):
                    print(f"    {cat:<30} {count}")
            if not found:
                print("    Run: dotfiles skills install")
            sys.exit(0)
    elif args.command == "memory":
        from pathlib import Path
        from .project_memory import (
            run_memory_check,
            run_memory_init,
            run_memory_list,
            run_memory_migrate,
        )

        repo = Path(args.repo)
        if args.memory_command == "init":
            sys.exit(run_memory_init(repo))
        if args.memory_command == "list":
            sys.exit(run_memory_list(repo, as_json=args.json))
        if args.memory_command == "check":
            sys.exit(run_memory_check(repo, as_json=args.json))
        if args.memory_command == "migrate":
            sys.exit(run_memory_migrate(repo, apply=args.apply))
    elif args.command == "claude":
        from . import RESOURCES_DIR
        from .claude_plugins import run_claude_setup
        groups = ["default"] + (args.extra_groups or [])
        statuses = run_claude_setup(
            resources_dir=RESOURCES_DIR,
            groups=groups,
            dry_run=args.dry_run,
        )
        # Non-zero exit if any integration failed outright (not auth-only)
        failed = [s for s in statuses if not s.installed and not args.dry_run
                  and not s.message.startswith("command not found")]
        sys.exit(1 if failed else 0)


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
