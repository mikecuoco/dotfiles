"""``dotfiles install`` and ``dotfiles status``.

Dotfile installation itself is chezmoi's job (see :mod:`dotfiles.chezmoi` and
``home/`` at the repository root). What remains here is the orchestration the
CLI adds on top: choosing a profile, running the two Code Ocean passes, and
installing the first-party agent skills, which chezmoi does not manage.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from . import RESOURCES_DIR, chezmoi
from .agent_skills import run_bundled_skills_setup


def run_install(
    profile: Optional[str] = None,
    dry_run: bool = False,
    quiet: bool = False,
    refresh: bool = False,
) -> int:
    """Apply the profile with chezmoi, then install bundled skills.

    With *refresh*, the chezmoi source repository is pulled first, so the
    dotfiles themselves update and not just the package. This is what
    ``dotfiles update`` uses.
    """
    try:
        if refresh and not dry_run:
            rc = chezmoi.update(quiet=quiet)
        else:
            rc = chezmoi.apply(profile=profile, dry_run=dry_run, quiet=quiet)
    except chezmoi.ChezmoiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if rc:
        return rc

    # First-party skills are local, portable resources and are part of the core
    # install. Downloaded GPTomics skill groups remain opt-in through
    # ``dotfiles skills install``.
    if not quiet:
        print("\nAgent skills")
    home = Path.home()
    failed = False
    for label, target in (
        ("Claude Code", claude_skills_dir(home)),
        ("Codex", home / ".agents" / "skills"),
    ):
        if not quiet:
            print(f"  {label}")
        statuses = run_bundled_skills_setup(
            RESOURCES_DIR, target, dry_run=dry_run, quiet=quiet
        )
        if not dry_run:
            failed = failed or any(not s.installed for s in statuses)

    return 1 if failed else 0


def claude_skills_dir(home: Optional[Path] = None) -> Path:
    """Where Claude Code skills belong for the active platform.

    Mirrors the capsule split in ``home/.chezmoiignore``: on Code Ocean the
    agent tree lives in the versioned capsule so it survives a rebuild.
    """
    capsule = chezmoi.capsule_dir()
    base = capsule if capsule.is_dir() else (home or Path.home())
    return base / ".claude" / "skills"


def run_status() -> int:
    """Report what chezmoi would change. Returns 0 when everything matches."""
    try:
        profile = chezmoi.active_profile()
        if not profile:
            print("dotfiles not installed. Run: dotfiles install")
            return 1

        print(f"Profile: {profile}")
        source = chezmoi.source_dir()
        if source:
            print(f"Source:  {source}")
        changes = chezmoi.status()
    except chezmoi.ChezmoiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not changes:
        print("\nAll managed files are up to date.")
        return 0

    # chezmoi status prints two status columns then the path, in the style of
    # `git status --short`.
    print(f"\nOut of date ({len(changes)}):")
    for line in changes:
        print(f"  {line}")
    print("\nRun: dotfiles install")
    return 1
