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
        "--home",
        metavar="DIR",
        help="Override home directory (useful for testing)",
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

    # ── claude-stats ─────────────────────────────────────────────────────────
    sub.add_parser(
        "claude-stats",
        help="Report Claude context budget (lines, words, estimated tokens per CLAUDE.md)",
    )

    # ── skills ───────────────────────────────────────────────────────────────
    p_skills = sub.add_parser(
        "skills",
        help="Manage GPTomics bioSkills (bioinformatics skill files for Claude Code)",
    )
    skills_sub = p_skills.add_subparsers(
        dest="skills_command",
        metavar="SUBCOMMAND",
    )
    skills_sub.required = True

    p_skills_install = skills_sub.add_parser(
        "install",
        help="Clone bioSkills repo and install skill files into ~/.claude/skills/",
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
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making any changes",
    )

    p_skills_update = skills_sub.add_parser(
        "update",
        help="Pull latest bioSkills repo and refresh any changed skill files",
    )
    p_skills_update.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making any changes",
    )

    skills_sub.add_parser(
        "status",
        help="Show how many bio-* skill files are installed in ~/.claude/skills/",
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

    match args.command:
        case "install":
            from pathlib import Path
            from .install import run_install
            home = Path(args.home) if args.home else None
            ok = run_install(profile=args.profile, dry_run=args.dry_run, home=home)
            sys.exit(0 if ok else 1)

        case "doctor":
            from .doctor import run_doctor
            sys.exit(run_doctor(as_json=args.json))

        case "auth":
            from .auth import run_auth
            sys.exit(run_auth())

        case "status":
            from .install import run_status
            sys.exit(run_status())

        case "profiles":
            _list_profiles()

        case "claude-stats":
            from .claude_stats import run_claude_stats
            sys.exit(run_claude_stats())

        case "skills":
            from pathlib import Path
            from . import RESOURCES_DIR
            from .claude_skills import run_skills_setup, check_skill_statuses

            cache_dir  = Path.home() / ".local" / "share" / "dotfiles" / "bioskills"
            target_dir = Path.home() / ".claude" / "skills"

            match args.skills_command:
                case "install":
                    groups = ["default"] + (args.extra_groups or [])
                    statuses = run_skills_setup(
                        resources_dir=RESOURCES_DIR,
                        groups=groups,
                        cache_dir=cache_dir,
                        target_dir=target_dir,
                        dry_run=args.dry_run,
                    )
                    failed = [s for s in statuses if not s.installed and not args.dry_run]
                    sys.exit(1 if failed else 0)

                case "update":
                    # Re-pull and refresh; re-uses run_skills_setup which always pulls
                    # when .git already exists.
                    from dotfiles.claude_skills import load_skills_config
                    cfg = load_skills_config(RESOURCES_DIR)
                    all_groups = list(cfg.groups)
                    statuses = run_skills_setup(
                        resources_dir=RESOURCES_DIR,
                        groups=all_groups,
                        cache_dir=cache_dir,
                        target_dir=target_dir,
                        dry_run=args.dry_run,
                        update=True,
                    )
                    failed = [s for s in statuses if not s.installed and not args.dry_run]
                    sys.exit(1 if failed else 0)

                case "status":
                    statuses = check_skill_statuses(target_dir)
                    total = len(statuses)
                    if total == 0:
                        print("  – no bio-* skills installed in ~/.claude/skills/")
                        print("    Run: dotfiles skills install")
                    else:
                        from collections import Counter
                        by_cat = Counter(s.category for s in statuses)
                        print(f"  {total} bioSkill(s) installed in {target_dir}")
                        for cat, count in sorted(by_cat.items()):
                            print(f"    {cat:<30} {count}")
                    sys.exit(0)

        case "claude":
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
