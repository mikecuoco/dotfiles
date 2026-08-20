"""Portable Claude Code and Codex skill management.

Provides idempotent install/check logic for first-party skill directories
bundled with these dotfiles and bioinformatics skill files sourced from the
GPTomics/bioSkills GitHub repository.

All subprocess calls (git) are isolated to ``_run_git()`` so they can be
mocked in tests.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import Optional

from ._toml import tomllib


_SKILL_NAME_RE = re.compile(r"[a-z0-9-]{1,64}")
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---(?:\s*\n|\Z)", re.DOTALL)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class SkillsConfig:
    """Top-level configuration loaded from ``agents/skills.toml``."""

    repo_url: str
    categories: list[str]   # empty = no filter (install every category)


@dataclass
class SkillStatus:
    """Result of installing or checking one skill."""

    name: str           # e.g. "bio-single-cell-clustering"
    category: str       # e.g. "single-cell"
    installed: bool
    message: str        # install/update/removal result or error text


@dataclass(frozen=True)
class SkillMetadata:
    """Portable Agent Skills metadata used by both Claude Code and Codex."""

    name: str
    description: str


def _unquote_yaml_scalar(value: str) -> str:
    """Decode the simple quoted or unquoted scalars used by skill metadata."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        quote = value[0]
        if quote == '"':
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = value[1:-1]
        else:
            value = value[1:-1].replace("''", "'")
    return value.strip()


def _parse_skill_metadata_text(text: str) -> SkillMetadata:
    """Parse the portable ``name`` and ``description`` frontmatter fields."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("missing YAML frontmatter")

    values: dict[str, str] = {}
    lines = match.group("body").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith((" ", "\t")) or ":" not in line:
            index += 1
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        if key not in {"name", "description"}:
            index += 1
            continue
        if raw in {"|", ">"}:
            block: list[str] = []
            index += 1
            while index < len(lines) and (
                not lines[index].strip() or lines[index].startswith((" ", "\t"))
            ):
                block.append(lines[index].strip())
                index += 1
            values[key] = ("\n" if raw == "|" else " ").join(block).strip()
            continue
        values[key] = _unquote_yaml_scalar(raw)
        index += 1

    name = values.get("name", "")
    description = values.get("description", "")
    if not name:
        raise ValueError("missing skill name")
    if not _SKILL_NAME_RE.fullmatch(name):
        raise ValueError(f"invalid skill name: {name!r}")
    if not description:
        raise ValueError("missing skill description")
    return SkillMetadata(name=name, description=description)


def _read_skill_metadata(path: Path) -> SkillMetadata:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot read SKILL.md: {exc}") from exc
    return _parse_skill_metadata_text(text)


# ── Config loading ────────────────────────────────────────────────────────────

def load_skills_config(resources_dir: Path) -> SkillsConfig:
    """Load bioSkills declarations from ``agents/skills.toml``."""
    path = resources_dir / "agents" / "skills.toml"
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)
    return SkillsConfig(
        repo_url=raw.get("repo", {}).get("url", ""),
        categories=list(raw.get("categories", [])),
    )


# ── Git interaction ───────────────────────────────────────────────────────────

def _run_git(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Run ``git <args>`` and return the completed process."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _try_git(args: list[str], label: str) -> bool:
    """Run a git command, printing ``✗ <label> failed: …`` on any failure."""
    try:
        result = _run_git(args)
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"  ✗ {label} failed: {exc}", file=sys.stderr)
        return False
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "unknown error").strip()[:200]
        print(f"  ✗ {label} failed: {err}", file=sys.stderr)
        return False
    return True


def _ensure_repo(repo_url: str, cache_dir: Path, update: bool = False) -> bool:
    """Clone the bioSkills repo into *cache_dir*, pulling when *update*.

    Returns True on success, False if git is unavailable or the operation
    fails. Without *update* an existing clone is left alone: `dotfiles install`
    runs on every shell setup and should not hit the network each time.
    """
    if not shutil.which("git"):
        print("  ✗ git not found — cannot fetch bioSkills repo", file=sys.stderr)
        return False

    if (cache_dir / ".git").exists():
        if not update:
            return True
        return _try_git(
            ["-C", str(cache_dir), "pull", "--ff-only", "--quiet"], "git pull"
        )

    # First-time clone (shallow for speed).
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    return _try_git(
        ["clone", "--depth=1", "--quiet", repo_url, str(cache_dir)], "git clone"
    )


# ── Skill discovery ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DiscoveredSkill:
    """One skill in the cloned repository, ready to install."""

    category: str
    installed_name: str   # the name declared in the skill's own frontmatter
    source: Path          # the skill directory, not just its SKILL.md


def _discover_skills(cache_dir: Path, categories: list[str]) -> list[DiscoveredSkill]:
    """Return installable skills from the cache, filtered by *categories*.

    An empty *categories* installs everything.

    The installed name is the one the skill declares for itself rather than one
    derived from its path. Upstream already namespaces every skill with a
    ``bio-`` prefix and de-duplicates the category word where it would repeat
    (``alignment/alignment-io`` declares ``bio-alignment-io``, not
    ``bio-alignment-alignment-io``). Deriving the name mechanically meant
    rewriting the frontmatter of every skill whose author disagreed; honouring
    the declared name means the files can be installed untouched.
    """
    category_filter = set(categories)
    seen: set[str] = set()
    results: list[DiscoveredSkill] = []

    for skill_md in sorted(cache_dir.rglob("SKILL.md")):
        skill_dir = skill_md.parent
        category_dir = skill_dir.parent
        # Expected layout: <cache>/<category>/<skill>/SKILL.md. Anything at a
        # different depth is repository furniture, not a skill.
        if category_dir == cache_dir or category_dir.parent != cache_dir:
            continue
        if category_filter and category_dir.name not in category_filter:
            continue

        try:
            name = _read_skill_metadata(skill_md).name
        except ValueError:
            continue
        if not _SKILL_NAME_RE.fullmatch(name) or name in seen:
            continue

        seen.add(name)
        results.append(DiscoveredSkill(category_dir.name, name, skill_dir))

    return results


# ── bioSkills installation ───────────────────────────────────────────────────

#: Every installed bioSkill directory carries this prefix, which is what makes
#: pruning safe: anything matching it and not currently discovered is ours to
#: remove, and nothing else is touched.
BIO_PREFIX = "bio-"


def run_skills_setup(
    resources_dir: Path,
    cache_dir: Optional[Path] = None,
    target_dir: Optional[Path] = None,
    dry_run: bool = False,
    update: bool = False,
    link: Optional[bool] = None,
) -> list[SkillStatus]:
    """Install the configured GPTomics bioSkills.

    First-party skills are not handled here -- they live in the chezmoi source
    and are installed by ``chezmoi apply``.

    Args:
        resources_dir: path to the bundled ``resources/`` directory.
        cache_dir:     clone location
                       (default: ``~/.local/share/dotfiles/bioskills``).
        target_dir:    skill directory
                       (default: ``~/.claude/skills``). ``~/.agents/skills`` is
                       a symlink to it, so there is only ever one destination.
        dry_run:       report what would be done without making changes.
        update:        pull even when the repository already exists.
        link:          install as symlinks into the cache rather than copies.
                       Defaults to copying only where the target must outlive
                       the cache -- see :func:`_should_link`.
    """
    if cache_dir is None:
        cache_dir = Path.home() / ".local" / "share" / "dotfiles" / "bioskills"
    if target_dir is None:
        target_dir = Path.home() / ".claude" / "skills"
    if link is None:
        link = _should_link(target_dir)

    config = load_skills_config(resources_dir)
    scope = ", ".join(config.categories) if config.categories else "all categories"

    if dry_run:
        print(f"  [dry] would clone/pull {config.repo_url} → {cache_dir}")
        print(f"  [dry] would install {scope} → {target_dir}")
        return []

    if not _ensure_repo(config.repo_url, cache_dir, update=update):
        return []
    print(f"  ✓ repo ready: {cache_dir}")

    skills = _discover_skills(cache_dir, config.categories)
    if not skills:
        print(f"  – no SKILL.md files found for {scope}", file=sys.stderr)
        return []

    target_dir.mkdir(parents=True, exist_ok=True)
    statuses = [_install_one(skill, target_dir / skill.installed_name, link)
                for skill in skills]
    statuses.extend(_prune(target_dir, {s.installed_name for s in skills}))

    _summarise(statuses, target_dir, link)
    return statuses


def _should_link(target_dir: Path) -> bool:
    """Whether skills may be symlinked into the cache rather than copied.

    Symlinks make updates free and keep one copy on disk, but they only work
    while the cache outlives them. The Code Ocean capsule is versioned and
    restored independently of ``$HOME``, so a capsule-resident skill pointing
    at a cache in ``$HOME`` would dangle after a rebuild. Those get real files.
    """
    capsule = Path(os.environ.get("DOTFILES_CAPSULE_DIR", "/root/capsule"))
    if not capsule.is_dir():
        return True
    # Both sides must be resolved before comparing: on macOS /var is a symlink
    # to /private/var, so an unresolved prefix check silently never matches.
    # Path.is_relative_to is 3.9+, and this package supports 3.8.
    target = str(target_dir.resolve())
    root = str(capsule.resolve())
    return not (target == root or target.startswith(root + os.sep))


def _install_one(skill: DiscoveredSkill, dest: Path, link: bool) -> SkillStatus:
    """Install one skill directory, replacing any previous managed copy."""
    def status(installed: bool, message: str) -> SkillStatus:
        return SkillStatus(skill.installed_name, skill.category, installed, message)

    try:
        if dest.is_symlink():
            if link and Path(os.readlink(str(dest))) == skill.source:
                return status(True, "unchanged")
            dest.unlink()
        elif dest.exists():
            if not link and _dirs_equal(skill.source, dest):
                return status(True, "unchanged")
            shutil.rmtree(dest)

        if link:
            dest.symlink_to(skill.source, target_is_directory=True)
        else:
            # The whole directory, not just SKILL.md: skills ship usage guides,
            # examples and scripts that the skill body references.
            shutil.copytree(skill.source, dest)
    except OSError as exc:
        return status(False, f"install failed: {exc}")

    return status(True, "linked" if link else "installed")


def _dirs_equal(src: Path, dst: Path) -> bool:
    """Whether *dst* already holds exactly the contents of *src*."""
    src_files = {p.relative_to(src) for p in src.rglob("*") if p.is_file()}
    dst_files = {p.relative_to(dst) for p in dst.rglob("*") if p.is_file()}
    if src_files != dst_files:
        return False
    return all(
        (src / rel).read_bytes() == (dst / rel).read_bytes() for rel in src_files
    )


def _prune(target_dir: Path, keep: set) -> list[SkillStatus]:
    """Remove previously installed bio-* skills that are no longer selected.

    This is what narrowing ``categories`` in skills.toml acts on. Only the
    ``bio-`` namespace is considered, so first-party and hand-made skills are
    never candidates.
    """
    statuses = []
    for path in sorted(target_dir.glob(f"{BIO_PREFIX}*")):
        if path.name in keep:
            continue
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
        except OSError as exc:
            statuses.append(SkillStatus(path.name, "removed", False, f"removal failed: {exc}"))
            continue
        statuses.append(SkillStatus(path.name, "removed", True, "removed"))
    return statuses


def _summarise(statuses: list, target_dir: Path, link: bool) -> None:
    """Print one line per outcome kind rather than one per skill.

    With the full catalogue selected this is several hundred skills; a per-skill
    line buries anything that actually went wrong.
    """
    counts: dict = {}
    for status in statuses:
        counts[status.message.split(":")[0]] = counts.get(status.message.split(":")[0], 0) + 1
    verb = "symlinked into the cache" if link else "copied"
    print(f"  bioSkills → {target_dir} ({verb})")
    for message, count in sorted(counts.items()):
        print(f"    {message:<16} {count}")
    for status in statuses:
        if not status.installed:
            print(f"  ✗ {status.name}: {status.message}", file=sys.stderr)


# ── Read-only status (used by doctor) ─────────────────────────────────────────

def check_skill_statuses(target_dir: Optional[Path] = None) -> list[SkillStatus]:
    """Return statuses for every installed skill, first-party or GPTomics.

    Used by ``dotfiles doctor``.  Never raises; returns an empty list when the
    target directory does not exist.
    """
    if target_dir is None:
        target_dir = Path.home() / ".claude" / "skills"

    if not target_dir.exists():
        return []

    # Anything under the bio- namespace came from the GPTomics repository;
    # everything else is first-party and installed by chezmoi.
    return [
        _installed_status(
            skill_file.parent.name,
            skill_file,
            "bioinformatics"
            if skill_file.parent.name.startswith(BIO_PREFIX)
            else "first-party",
        )
        for skill_file in sorted(target_dir.glob("*/SKILL.md"))
    ]


def _installed_status(name: str, skill_md: Path, category: str) -> SkillStatus:
    """Report whether an installed SKILL.md parses and matches its directory."""
    try:
        metadata = _read_skill_metadata(skill_md)
    except ValueError as exc:
        return SkillStatus(name, category, False, f"invalid skill: {exc}")
    installed = metadata.name == name
    return SkillStatus(
        name,
        category,
        installed,
        "installed" if installed else "metadata name does not match directory",
    )
