"""Portable Claude Code and Codex skill management.

Provides idempotent install/check logic for first-party skill directories
bundled with these dotfiles and bioinformatics skill files sourced from the
GPTomics/bioSkills GitHub repository.

All subprocess calls (git) are isolated to ``_run_git()`` so they can be
mocked in tests.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import Optional

from ._toml import tomllib


_MANAGED_SKILLS_FILE = ".dotfiles-managed-skills.json"
_SKILL_NAME_RE = re.compile(r"[a-z0-9-]{1,64}")
# Build and editor artifacts that may sit in a source skill directory but must
# never be copied into an installed skill or recorded in the managed registry.
_SKILL_ARTIFACT_DIRS = frozenset({"__pycache__", ".ipynb_checkpoints", ".pytest_cache"})
_SKILL_ARTIFACT_SUFFIXES = frozenset({".pyc", ".pyo"})
_SKILL_ARTIFACT_NAMES = frozenset({".DS_Store"})
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---(?:\s*\n|\Z)", re.DOTALL)
_NAME_LINE_RE = re.compile(r"(?m)^name:\s*[^\n]+$")


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SkillGroupConfig:
    """Configuration for a single bioSkills installation group."""

    name: str
    description: str
    categories: list[str]   # empty = no filter (install all)


@dataclass
class SkillsConfig:
    """Top-level configuration loaded from ``common/agents/skills.toml``."""

    repo_url: str
    groups: dict[str, SkillGroupConfig]


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


def _portable_skill_bytes(path: Path, installed_name: str) -> bytes:
    """Return a validated SKILL.md with its metadata name namespaced."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot read SKILL.md: {exc}") from exc
    _parse_skill_metadata_text(text)
    if not _SKILL_NAME_RE.fullmatch(installed_name):
        raise ValueError(f"invalid installed skill name: {installed_name!r}")
    if not _NAME_LINE_RE.search(text):
        raise ValueError("skill name must be a single-line frontmatter field")
    rendered = _NAME_LINE_RE.sub(f"name: {installed_name}", text, count=1)
    _parse_skill_metadata_text(rendered)
    return rendered.encode("utf-8")


# ── Config loading ────────────────────────────────────────────────────────────

def load_skills_config(resources_dir: Path) -> SkillsConfig:
    """Load bioSkills declarations from ``common/agents/skills.toml``."""
    path = resources_dir / "common" / "agents" / "skills.toml"
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

def _discover_bundled_skills(resources_dir: Path) -> list[Path]:
    """Return first-party skill directories bundled with the dotfiles."""
    root = resources_dir / "common" / "agents" / "skills"
    if not root.is_dir():
        return []
    return sorted(
        path for path in root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


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


# ── First-party skill setup ──────────────────────────────────────────────────

def _read_managed_skills(target_dir: Path) -> dict[str, list[str]]:
    """Read the first-party skill registry, returning an empty registry on error."""
    path = target_dir / _MANAGED_SKILLS_FILE
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    skills = raw.get("skills", {}) if isinstance(raw, dict) else {}
    if not isinstance(skills, dict):
        return {}
    return {
        name: [item for item in files if isinstance(item, str) and _safe_relative_path(item)]
        for name, files in skills.items()
        if (
            isinstance(name, str)
            and _SKILL_NAME_RE.fullmatch(name)
            and isinstance(files, list)
        )
    }


def _write_managed_skills(target_dir: Path, skills: dict[str, list[str]]) -> None:
    """Write the first-party skill registry only when its content changed."""
    path = target_dir / _MANAGED_SKILLS_FILE
    content = json.dumps({"skills": skills}, indent=2, sort_keys=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _is_skill_artifact(relative: PurePosixPath) -> bool:
    """Return whether a skill-relative path is a build or editor artifact."""
    if any(part in _SKILL_ARTIFACT_DIRS for part in relative.parts):
        return True
    return relative.suffix in _SKILL_ARTIFACT_SUFFIXES or relative.name in _SKILL_ARTIFACT_NAMES


def _skill_files(skill_dir: Path) -> dict[str, Path]:
    """Return relative path → source path for the installable files in a skill.

    Build and editor artifacts are excluded so stale bytecode in a source
    directory is never copied into an installed skill.
    """
    files: dict[str, Path] = {}
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = PurePosixPath(path.relative_to(skill_dir).as_posix())
        if _is_skill_artifact(relative):
            continue
        files[str(relative)] = path
    return files


def _safe_relative_path(value: str) -> bool:
    """Return whether a registry path stays inside its skill directory."""
    if not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and path != PurePosixPath(".") and ".." not in path.parts


def _destination_path(skill_dir: Path, relative: str) -> Path:
    """Resolve a safe registry-relative path beneath a skill directory."""
    if not _safe_relative_path(relative):
        raise OSError(f"unsafe managed skill path: {relative!r}")
    return skill_dir.joinpath(*PurePosixPath(relative).parts)


def _prepare_destination_parent(skill_dir: Path, relative: str) -> Path:
    """Create destination parents while refusing nested symlink traversal."""
    destination = _destination_path(skill_dir, relative)
    current = skill_dir
    for part in PurePosixPath(relative).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise OSError(f"refusing nested symlink in managed skill: {current}")
        if current.exists() and not current.is_dir():
            raise OSError(f"managed skill parent is not a directory: {current}")
        current.mkdir(exist_ok=True)
    return destination


def _validate_destination(skill_dir: Path, relative: str) -> Path:
    """Validate an existing destination path without creating or changing it."""
    destination = _destination_path(skill_dir, relative)
    current = skill_dir
    for part in PurePosixPath(relative).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise OSError(f"refusing nested symlink in managed skill: {current}")
        if current.exists() and not current.is_dir():
            raise OSError(f"managed skill parent is not a directory: {current}")
    return destination


def _same_file(src: Path, dst: Path) -> bool:
    """Return whether two files have identical bytes without raising."""
    try:
        return dst.is_file() and src.read_bytes() == dst.read_bytes()
    except OSError:
        return False


def _bundled_action(
    source_files: dict[str, Path],
    previous_files: set[str],
    destination: Path,
) -> str:
    """Describe whether a managed skill needs installation or an update."""
    if not destination.exists():
        return "install"
    if previous_files != set(source_files):
        return "update"
    if any(not _same_file(src, destination / rel) for rel, src in source_files.items()):
        return "update"
    return "unchanged"


def _prune_empty_parents(path: Path, stop: Path) -> None:
    """Remove empty directories beneath *stop* after deleting managed files."""
    parent = path.parent
    while parent != stop and stop in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def run_bundled_skills_setup(
    resources_dir: Path,
    target_dir: Optional[Path] = None,
    dry_run: bool = False,
    quiet: bool = False,
) -> list[SkillStatus]:
    """Install portable bundled skill directories for one agent."""
    if target_dir is None:
        target_dir = Path.home() / ".claude" / "skills"

    sources = _discover_bundled_skills(resources_dir)
    source_names = {source.name for source in sources}
    registry = _read_managed_skills(target_dir)
    updated_registry = dict(registry)
    statuses: list[SkillStatus] = []

    for source in sources:
        name = source.name
        destination = target_dir / name
        managed = name in registry

        try:
            metadata = _read_skill_metadata(source / "SKILL.md")
            if metadata.name != name:
                raise ValueError(
                    f"folder name {name!r} does not match metadata name {metadata.name!r}"
                )
        except ValueError as exc:
            status = SkillStatus(name, "first-party", False, f"invalid skill: {exc}")
            statuses.append(status)
            if not quiet:
                _print_skill_status(status)
            continue

        if (destination.exists() or destination.is_symlink()) and not managed:
            status = SkillStatus(
                name,
                "first-party",
                False,
                "conflict: existing skill is not managed by dotfiles",
            )
            statuses.append(status)
            if not quiet:
                _print_skill_status(status)
            continue

        if managed and (destination.is_symlink() or (destination.exists() and not destination.is_dir())):
            status = SkillStatus(
                name,
                "first-party",
                False,
                "conflict: managed skill path is not a directory",
            )
            statuses.append(status)
            if not quiet:
                _print_skill_status(status)
            continue

        source_files = _skill_files(source)
        previous_files = set(registry.get(name, []))
        action = _bundled_action(source_files, previous_files, destination)

        try:
            # Check the whole update before copying so a newly bundled path can
            # never overwrite a user-created file inside a managed skill.
            for rel in source_files:
                dst = _validate_destination(destination, rel)
                if rel not in previous_files and (dst.exists() or dst.is_symlink()):
                    raise OSError(f"unmanaged file conflicts with bundled path: {dst}")
        except OSError as exc:
            status = SkillStatus(name, "first-party", False, f"copy failed: {exc}")
            statuses.append(status)
            if not quiet:
                _print_skill_status(status)
            continue

        if dry_run:
            message = "already installed" if action == "unchanged" else f"would {action}"
            status = SkillStatus(name, "first-party", True, message)
            statuses.append(status)
            if not quiet:
                _print_skill_status(status)
            continue

        try:
            destination.mkdir(parents=True, exist_ok=True)
            for rel, src in source_files.items():
                dst = _prepare_destination_parent(destination, rel)
                if _same_file(src, dst):
                    continue
                if dst.is_symlink():
                    dst.unlink()
                shutil.copy2(src, dst)

            for rel in previous_files - set(source_files):
                obsolete = _destination_path(destination, rel)
                if obsolete.is_file() or obsolete.is_symlink():
                    obsolete.unlink()
                    _prune_empty_parents(obsolete, destination)

            updated_registry[name] = sorted(source_files)
        except OSError as exc:
            status = SkillStatus(name, "first-party", False, f"copy failed: {exc}")
        else:
            messages = {
                "install": "installed",
                "update": "updated",
                "unchanged": "already installed",
            }
            status = SkillStatus(name, "first-party", True, messages[action])

        statuses.append(status)
        if not quiet:
            _print_skill_status(status)

    # Remove bundled skills that this dotfiles version no longer ships. Only
    # registry-owned files are deleted, so user-created files in the same
    # directory survive the migration.
    for name in sorted(set(registry) - source_names):
        destination = target_dir / name

        if dry_run:
            status = SkillStatus(name, "first-party", True, "would remove")
            statuses.append(status)
            if not quiet:
                _print_skill_status(status)
            continue

        try:
            if destination.is_symlink() or (
                destination.exists() and not destination.is_dir()
            ):
                raise OSError(
                    f"refusing managed skill path that is not a directory: {destination}"
                )
            for rel in registry[name]:
                obsolete = _validate_destination(destination, rel)
                if obsolete.is_file() or obsolete.is_symlink():
                    obsolete.unlink()
                    _prune_empty_parents(obsolete, destination)
            if destination.is_dir():
                try:
                    destination.rmdir()
                except OSError:
                    pass
            updated_registry.pop(name, None)
        except OSError as exc:
            status = SkillStatus(name, "first-party", False, f"remove failed: {exc}")
        else:
            status = SkillStatus(name, "first-party", True, "removed")

        statuses.append(status)
        if not quiet:
            _print_skill_status(status)

    if not dry_run and updated_registry != registry:
        _write_managed_skills(target_dir, updated_registry)

    return statuses


# ── Combined setup ────────────────────────────────────────────────────────────

def run_skills_setup(
    resources_dir: Path,
    groups: Optional[list[str]] = None,
    cache_dir: Optional[Path] = None,
    target_dir: Optional[Path] = None,
    codex_target_dir: Optional[Path] = None,
    dry_run: bool = False,
    update: bool = False,
) -> list[SkillStatus]:
    """Install bundled first-party skills and selected GPTomics bioSkills.

    Args:
        resources_dir: path to the dotfiles ``resources/`` directory.
        groups:        list of group names to install (default: ``["default"]``).
        cache_dir:     where to cache the cloned repo
                       (default: ``~/.local/share/dotfiles/bioskills/``).
        target_dir:    Claude Code skill directory
                       (default: ``~/.claude/skills/``).
        codex_target_dir: optional Codex destination. Both agents use the
                       portable ``<name>/SKILL.md`` directory layout.
        dry_run:       report what would be done without making changes.
        update:        force a git pull even when the repo already exists
                       (implicit when calling ``dotfiles skills update``).

    Returns:
        A list of :class:`SkillStatus` for each skill processed.
    """
    if groups is None:
        groups = ["default"]
    if cache_dir is None:
        cache_dir = Path.home() / ".local" / "share" / "dotfiles" / "bioskills"
    if target_dir is None:
        target_dir = Path.home() / ".claude" / "skills"

    statuses = run_bundled_skills_setup(resources_dir, target_dir, dry_run=dry_run)
    if codex_target_dir is not None and codex_target_dir != target_dir:
        statuses.extend(
            run_bundled_skills_setup(
                resources_dir,
                codex_target_dir,
                dry_run=dry_run,
            )
        )
    config = load_skills_config(resources_dir)

    # Collect categories for the requested groups.
    all_categories: list[str] = []
    install_all = False
    valid_groups = 0
    for group_name in groups:
        if group_name not in config.groups:
            print(
                f"  ✗ unknown skills group: {group_name!r} "
                f"(available: {', '.join(sorted(config.groups))})",
                file=sys.stderr,
            )
            continue
        valid_groups += 1
        g = config.groups[group_name]
        if not g.categories:
            install_all = True  # "all" group — no category filter
        else:
            all_categories.extend(g.categories)

    if valid_groups == 0:
        return statuses

    categories_to_install: list[str] = [] if install_all else all_categories

    # ── Clone / pull ──────────────────────────────────────────────────────────
    if dry_run:
        print(f"  [dry] would clone/pull {config.repo_url} → {cache_dir}")
    else:
        ok = _ensure_repo(config.repo_url, cache_dir)
        if not ok:
            return statuses
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
        print(f"  [dry] Claude target: {target_dir}")
        if codex_target_dir is not None and codex_target_dir != target_dir:
            print(f"  [dry] Codex target: {codex_target_dir}")
        return statuses

    skills = _discover_skills(cache_dir, categories_to_install)

    if not skills:
        scope = (
            "any category"
            if not categories_to_install
            else ", ".join(sorted(set(categories_to_install)))
        )
        print(f"  – no SKILL.md files found for {scope}", file=sys.stderr)
        return statuses

    # ── Copy skill files ──────────────────────────────────────────────────────
    target_dir.mkdir(parents=True, exist_ok=True)

    for category, skill_name, skill_md in skills:
        dest_name = f"bio-{category}-{skill_name}"
        dest = target_dir / dest_name / "SKILL.md"
        status = _install_one(category, dest_name, skill_md, dest)
        statuses.append(status)
        _print_skill_status(status)

        if codex_target_dir is not None and codex_target_dir != target_dir:
            codex_dest = codex_target_dir / dest_name / "SKILL.md"
            status = _install_one(category, dest_name, skill_md, codex_dest)
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
    try:
        src_bytes = _portable_skill_bytes(src, dest_name)
        dest.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as exc:
        return SkillStatus(dest_name, category, False, f"copy failed: {exc}")

    if dest.exists():
        if not dest.is_file():
            return SkillStatus(
                dest_name,
                category,
                False,
                "copy failed: destination is not a regular file",
            )
        try:
            if dest.read_bytes() == src_bytes:
                return SkillStatus(dest_name, category, True, "already installed")
            # Content changed (e.g. after a git pull) — overwrite.
            dest.write_bytes(src_bytes)
        except OSError as exc:
            return SkillStatus(dest_name, category, False, f"copy failed: {exc}")
        return SkillStatus(dest_name, category, True, "updated")

    try:
        dest.write_bytes(src_bytes)
    except OSError as exc:
        return SkillStatus(dest_name, category, False, f"copy failed: {exc}")

    return SkillStatus(dest_name, category, True, "installed")


def _print_skill_status(status: SkillStatus) -> None:
    if status.installed:
        if status.message.startswith("would "):
            icon = "[dry]"
        else:
            icon = "→" if status.message in ("installed", "updated") else "✓"
        print(f"  {icon} {status.name}: {status.message}")
    else:
        print(f"  ✗ {status.name}: {status.message}", file=sys.stderr)


# ── Read-only status (used by doctor) ─────────────────────────────────────────

def check_skill_statuses(target_dir: Optional[Path] = None) -> list[SkillStatus]:
    """Return statuses for managed first-party and installed GPTomics skills.

    Used by ``dotfiles doctor``.  Never raises; returns an empty list when the
    target directory does not exist.
    """
    if target_dir is None:
        target_dir = Path.home() / ".claude" / "skills"

    if not target_dir.exists():
        return []

    statuses: list[SkillStatus] = []
    for name in sorted(_read_managed_skills(target_dir)):
        skill_md = target_dir / name / "SKILL.md"
        try:
            metadata = _read_skill_metadata(skill_md)
        except ValueError as exc:
            statuses.append(
                SkillStatus(name, "first-party", False, f"invalid skill: {exc}")
            )
            continue
        installed = metadata.name == name
        statuses.append(
            SkillStatus(
                name,
                "first-party",
                installed,
                "installed" if installed else "metadata name does not match directory",
            )
        )

    for skill_file in sorted(target_dir.glob("bio-*/SKILL.md")):
        name = skill_file.parent.name
        try:
            metadata = _read_skill_metadata(skill_file)
        except ValueError as exc:
            statuses.append(
                SkillStatus(name, "bioinformatics", False, f"invalid skill: {exc}")
            )
            continue
        installed = metadata.name == name
        statuses.append(
            SkillStatus(
                name,
                "bioinformatics",
                installed,
                "installed" if installed else "metadata name does not match directory",
            )
        )

    return statuses
