"""GPTomics bioSkills management.

Provides idempotent install/check logic for bioinformatics skill files sourced
from the GPTomics/bioSkills GitHub repository.  Skills are plain markdown files
copied into ``~/.claude/skills/`` under the name ``bio-<category>-<skill>.md``.

All subprocess calls (git) are isolated to ``_run_git()`` so they can be
mocked in tests.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SkillGroupConfig:
    """Configuration for a single bioSkills installation group."""

    name: str
    description: str
    categories: list[str]   # empty = no filter (install all)


@dataclass
class SkillsConfig:
    """Top-level configuration loaded from ``claude/skills.toml``."""

    repo_url: str
    groups: dict[str, SkillGroupConfig]


@dataclass
class SkillStatus:
    """Result of installing or checking one skill file."""

    name: str           # e.g. "bio-single-cell-clustering"
    category: str       # e.g. "single-cell"
    installed: bool
    message: str        # "installed" | "already installed" | "skipped" | error text


# ── Config loading ────────────────────────────────────────────────────────────

def load_skills_config(resources_dir: Path) -> SkillsConfig:
    """Load bioSkills declarations from ``claude/skills.toml``."""
    path = resources_dir / "claude" / "skills.toml"
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    repo_url: str = raw.get("repo", {}).get("url", "")

    groups: dict[str, SkillGroupConfig] = {}
    for group_name, group_data in raw.get("groups", {}).items():
        groups[group_name] = SkillGroupConfig(
            name=group_name,
            description=group_data.get("description", ""),
            categories=list(group_data.get("categories", [])),
        )

    return SkillsConfig(repo_url=repo_url, groups=groups)


# ── Git interaction ───────────────────────────────────────────────────────────

def _run_git(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Run ``git <args>`` and return the completed process."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _ensure_repo(repo_url: str, cache_dir: Path) -> bool:
    """Clone or fast-forward-pull the bioSkills repo into *cache_dir*.

    Returns True on success, False if git is unavailable or the operation
    fails.
    """
    if not shutil.which("git"):
        print("  ✗ git not found — cannot fetch bioSkills repo", file=sys.stderr)
        return False

    if (cache_dir / ".git").exists():
        # Already cloned — attempt a fast-forward pull.
        try:
            result = _run_git(["-C", str(cache_dir), "pull", "--ff-only", "--quiet"])
        except (subprocess.TimeoutExpired, OSError) as exc:
            print(f"  ✗ git pull failed: {exc}", file=sys.stderr)
            return False
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "unknown error").strip()[:200]
            print(f"  ✗ git pull failed: {err}", file=sys.stderr)
            return False
        return True

    # First-time clone (shallow for speed).
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = _run_git(["clone", "--depth=1", "--quiet", repo_url, str(cache_dir)])
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"  ✗ git clone failed: {exc}", file=sys.stderr)
        return False
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "unknown error").strip()[:200]
        print(f"  ✗ git clone failed: {err}", file=sys.stderr)
        return False
    return True


# ── Skill discovery ───────────────────────────────────────────────────────────

def _discover_skills(
    cache_dir: Path,
    categories: list[str],
) -> list[tuple[str, str, Path]]:
    """Return ``(category, skill_name, skill_md_path)`` tuples from the cache.

    If *categories* is empty, all SKILL.md files are returned.  Otherwise only
    those whose immediate parent directory name (the category) is in the set.
    """
    category_filter: set[str] = set(categories)

    results: list[tuple[str, str, Path]] = []
    for skill_md in sorted(cache_dir.rglob("SKILL.md")):
        # Expected layout: <cache>/<category>/<skill-name>/SKILL.md
        # skill_md.parent      → <skill-name> dir
        # skill_md.parent.parent → <category> dir
        skill_dir = skill_md.parent
        category_dir = skill_dir.parent

        # Skip files that are not exactly two levels deep (e.g. root-level cruft)
        if category_dir == cache_dir:
            continue

        category = category_dir.name
        skill_name = skill_dir.name

        if category_filter and category not in category_filter:
            continue

        results.append((category, skill_name, skill_md))

    return results


# ── Setup ─────────────────────────────────────────────────────────────────────

def run_skills_setup(
    resources_dir: Path,
    groups: Optional[list[str]] = None,
    cache_dir: Optional[Path] = None,
    target_dir: Optional[Path] = None,
    dry_run: bool = False,
    update: bool = False,
) -> list[SkillStatus]:
    """Idempotently install bioSkills into *target_dir*.

    Args:
        resources_dir: path to the dotfiles ``resources/`` directory.
        groups:        list of group names to install (default: ``["default"]``).
        cache_dir:     where to cache the cloned repo
                       (default: ``~/.local/share/dotfiles/bioskills/``).
        target_dir:    where to write skill files
                       (default: ``~/.claude/skills/``).
        dry_run:       report what would be done without making changes.
        update:        force a git pull even when the repo already exists
                       (implicit when calling ``dotfiles skills update``).

    Returns:
        A list of :class:`SkillStatus` for each skill file processed.
    """
    if groups is None:
        groups = ["default"]
    if cache_dir is None:
        cache_dir = Path.home() / ".local" / "share" / "dotfiles" / "bioskills"
    if target_dir is None:
        target_dir = Path.home() / ".claude" / "skills"

    config = load_skills_config(resources_dir)

    # Collect categories for the requested groups.
    all_categories: list[str] = []
    install_all = False
    for group_name in groups:
        if group_name not in config.groups:
            print(
                f"  ✗ unknown skills group: {group_name!r} "
                f"(available: {', '.join(sorted(config.groups))})",
                file=sys.stderr,
            )
            continue
        g = config.groups[group_name]
        if not g.categories:
            install_all = True  # "all" group — no category filter
        else:
            all_categories.extend(g.categories)

    categories_to_install: list[str] = [] if install_all else all_categories

    # ── Clone / pull ──────────────────────────────────────────────────────────
    if dry_run:
        print(f"  [dry] would clone/pull {config.repo_url} → {cache_dir}")
    else:
        ok = _ensure_repo(config.repo_url, cache_dir)
        if not ok:
            return []
        print(f"  ✓ repo ready: {cache_dir}")

    # ── Discover skills ───────────────────────────────────────────────────────
    if dry_run:
        # Can't discover without a real cache; report intention only.
        scope = (
            "all categories"
            if not categories_to_install
            else ", ".join(sorted(set(categories_to_install)))
        )
        print(f"  [dry] would install skills for: {scope}")
        print(f"  [dry] target: {target_dir}")
        return []

    skills = _discover_skills(cache_dir, categories_to_install)

    if not skills:
        scope = (
            "any category"
            if not categories_to_install
            else ", ".join(sorted(set(categories_to_install)))
        )
        print(f"  – no SKILL.md files found for {scope}", file=sys.stderr)
        return []

    # ── Copy skill files ──────────────────────────────────────────────────────
    target_dir.mkdir(parents=True, exist_ok=True)

    statuses: list[SkillStatus] = []
    for category, skill_name, skill_md in skills:
        dest_name = f"bio-{category}-{skill_name}.md"
        dest = target_dir / dest_name
        status = _install_one(category, dest_name, skill_md, dest)
        statuses.append(status)
        _print_skill_status(status)

    return statuses


def _install_one(
    category: str,
    dest_name: str,
    src: Path,
    dest: Path,
) -> SkillStatus:
    """Copy *src* to *dest*, skipping if content is already identical."""
    src_bytes = src.read_bytes()

    if dest.exists():
        if dest.read_bytes() == src_bytes:
            return SkillStatus(dest_name, category, True, "already installed")
        # Content changed (e.g. after a git pull) — overwrite.
        dest.write_bytes(src_bytes)
        return SkillStatus(dest_name, category, True, "updated")

    try:
        dest.write_bytes(src_bytes)
    except OSError as exc:
        return SkillStatus(dest_name, category, False, f"copy failed: {exc}")

    return SkillStatus(dest_name, category, True, "installed")


def _print_skill_status(status: SkillStatus) -> None:
    if status.installed:
        icon = "→" if status.message in ("installed", "updated") else "✓"
        print(f"  {icon} {status.name}: {status.message}")
    else:
        print(f"  ✗ {status.name}: {status.message}", file=sys.stderr)


# ── Read-only status (used by doctor) ─────────────────────────────────────────

def check_skill_statuses(target_dir: Optional[Path] = None) -> list[SkillStatus]:
    """Return status for every ``bio-*.md`` file in *target_dir*.

    Used by ``dotfiles doctor``.  Never raises; returns an empty list when the
    target directory does not exist.
    """
    if target_dir is None:
        target_dir = Path.home() / ".claude" / "skills"

    if not target_dir.exists():
        return []

    statuses: list[SkillStatus] = []
    for skill_file in sorted(target_dir.glob("bio-*.md")):
        name = skill_file.stem           # e.g. "bio-single-cell-clustering"
        # Derive category from the second hyphen-separated segment (bio-<cat>-<skill>)
        parts = name.split("-", 2)       # ["bio", "<cat>", "<skill-with-hyphens>"]
        category = parts[1] if len(parts) >= 2 else "unknown"
        statuses.append(SkillStatus(name, category, True, "installed"))

    return statuses
