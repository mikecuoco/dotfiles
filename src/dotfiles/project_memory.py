"""Shared project-local memory support for Claude Code and Codex.

The ``.agents/memory/`` directory is a dotfiles convention, not a native
discovery path for either agent.  This module keeps the convention small,
inspectable, and safe to use from the CLI and doctor command.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


MEMORY_RELATIVE = Path(".agents") / "memory"
LEGACY_MEMORY_PATHS = (
    Path(".claude") / "memory",
    Path(".codex") / "memories",
    Path(".agents") / "memories",
)
MAX_MEMORY_LINES = 100
MAX_MEMORY_BYTES = 32 * 1024

_MEMORY_NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\.md")
_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[-_ ]+")
_SESSION_HEADING_RE = re.compile(
    r"(?mi)^##\s+(request|changes?|validation|remaining work|outcome|task status)\s*$"
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)"
    r"\s*[:=]\s*[\"']?(?!\$|<|redacted|example|placeholder)"
    r"[A-Za-z0-9_./+=-]{12,}"
)


@dataclass(frozen=True)
class MemoryEntry:
    """A concise list representation of one project memory."""

    name: str
    title: str
    lines: int


@dataclass(frozen=True)
class MemoryStatus:
    """One project-memory validation result."""

    path: str
    level: str  # "ok" | "info" | "warning" | "error"
    message: str

    @property
    def ok(self) -> bool:
        return self.level != "error"


@dataclass(frozen=True)
class MigrationAction:
    """A reviewable migration action for one legacy Markdown file."""

    source: str
    target: Optional[str]
    action: str  # "migrate" | "duplicate" | "review" | "conflict"
    message: str


def find_repo_root(start: Path) -> Path:
    """Return the nearest Git root, falling back to *start* itself."""
    current = start.expanduser().resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def project_memory_dir(repo: Path) -> Path:
    return find_repo_root(repo) / MEMORY_RELATIVE


def initialize_project_memory(repo: Path) -> Path:
    """Safely create the shared project memory directory."""
    root = find_repo_root(repo)
    agents_dir = root / ".agents"
    memory_dir = root / MEMORY_RELATIVE

    if agents_dir.is_symlink() or (agents_dir.exists() and not agents_dir.is_dir()):
        raise OSError(f"refusing .agents path that is not a directory: {agents_dir}")
    if memory_dir.is_symlink() or (memory_dir.exists() and not memory_dir.is_dir()):
        raise OSError(f"refusing memory path that is not a directory: {memory_dir}")

    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


def list_project_memories(repo: Path) -> list[MemoryEntry]:
    """List direct Markdown memories without returning their bodies."""
    memory_dir = project_memory_dir(repo)
    if not memory_dir.is_dir() or memory_dir.is_symlink():
        return []

    entries: list[MemoryEntry] = []
    for path in sorted(memory_dir.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        title = next(
            (line[2:].strip() for line in lines if line.startswith("# ")),
            "(missing title)",
        )
        entries.append(MemoryEntry(path.name, title, len(lines)))
    return entries


def check_project_memory(repo: Path) -> list[MemoryStatus]:
    """Validate the shared project memory directory and its direct files."""
    root = find_repo_root(repo)
    memory_dir = root / MEMORY_RELATIVE
    relative_dir = MEMORY_RELATIVE.as_posix() + "/"

    if memory_dir.is_symlink() or (memory_dir.exists() and not memory_dir.is_dir()):
        return [MemoryStatus(relative_dir, "error", "must be a regular directory")]
    if not memory_dir.exists():
        return [MemoryStatus(relative_dir, "info", "not initialized")]

    statuses = [MemoryStatus(relative_dir, "ok", "directory exists")]
    ignored = _is_git_ignored(root, MEMORY_RELATIVE / ".ignore-probe")
    if ignored is True:
        statuses.append(MemoryStatus(relative_dir, "ok", "ignored by Git"))
    elif ignored is False:
        statuses.append(MemoryStatus(relative_dir, "error", "not ignored by Git"))
    else:
        statuses.append(
            MemoryStatus(relative_dir, "warning", "could not verify Git ignore rule")
        )

    children = sorted(memory_dir.iterdir())
    if not children:
        statuses.append(MemoryStatus(relative_dir, "info", "contains no memories"))
        return statuses

    for path in children:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            statuses.append(MemoryStatus(relative, "error", "symlinks are not allowed"))
            continue
        if not path.is_file():
            statuses.append(
                MemoryStatus(relative, "error", "nested directories are not allowed")
            )
            continue
        errors = _memory_file_errors(path)
        if errors:
            statuses.extend(MemoryStatus(relative, "error", error) for error in errors)
        else:
            statuses.append(MemoryStatus(relative, "ok", "valid memory"))
    return statuses


def plan_legacy_migration(repo: Path, apply: bool = False) -> list[MigrationAction]:
    """Plan or apply safe, lossless copies from obsolete memory directories.

    Files that resemble session summaries or violate the current memory
    contract are left for manual review.  Legacy sources are never deleted.
    """
    root = find_repo_root(repo)
    target_dir = root / MEMORY_RELATIVE
    planned: dict[str, str] = {}
    actions: list[MigrationAction] = []

    for legacy_relative in LEGACY_MEMORY_PATHS:
        legacy_dir = root / legacy_relative
        if not legacy_dir.exists():
            continue
        if legacy_dir.is_symlink() or not legacy_dir.is_dir():
            actions.append(
                MigrationAction(
                    legacy_relative.as_posix(),
                    None,
                    "review",
                    "legacy path is not a regular directory",
                )
            )
            continue

        for source in sorted(legacy_dir.rglob("*")):
            if source.is_dir() and not source.is_symlink():
                continue
            actions.append(_plan_one_source(source, root, target_dir, planned, apply))

    return actions


def _plan_one_source(
    source: Path,
    root: Path,
    target_dir: Path,
    planned: dict[str, str],
    apply: bool,
) -> MigrationAction:
    """Plan (and optionally perform) the migration of one legacy file.

    *planned* is updated in place so that two legacy sources mapping to the same
    target are reported as a conflict rather than silently overwriting.
    """
    source_relative = source.relative_to(root).as_posix()
    if source.is_symlink() or not source.is_file() or source.suffix != ".md":
        return MigrationAction(
            source_relative,
            None,
            "review",
            "only regular Markdown files can migrate automatically",
        )

    try:
        data = source.read_bytes()
        text = data.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return MigrationAction(source_relative, None, "review", f"cannot read: {exc}")

    if len(_SESSION_HEADING_RE.findall(text)) >= 2:
        return MigrationAction(
            source_relative,
            None,
            "review",
            "session summary must be split into topic memories manually",
        )

    target_name = _migration_name(source.stem)
    target = target_dir / target_name
    target_relative = target.relative_to(root).as_posix()

    candidate_errors = _memory_text_errors(target_name, text, len(data))
    if candidate_errors:
        return MigrationAction(
            source_relative, target_relative, "review", "; ".join(candidate_errors)
        )

    if target.is_symlink():
        return MigrationAction(
            source_relative, target_relative, "conflict", "target is a symlink"
        )

    if target.exists():
        try:
            same = target.is_file() and target.read_bytes() == data
        except OSError:
            same = False
        return MigrationAction(
            source_relative,
            target_relative,
            "duplicate" if same else "conflict",
            "already migrated" if same else "target has different content",
        )

    digest = hashlib.sha256(data).hexdigest()
    if target_relative in planned:
        same = planned[target_relative] == digest
        return MigrationAction(
            source_relative,
            target_relative,
            "duplicate" if same else "conflict",
            "duplicate legacy copy" if same else "two sources map to one target",
        )

    planned[target_relative] = digest
    if not apply:
        return MigrationAction(
            source_relative, target_relative, "migrate", "would copy"
        )

    if _is_git_ignored(root, MEMORY_RELATIVE / ".ignore-probe") is not True:
        planned.pop(target_relative, None)
        return MigrationAction(
            source_relative,
            target_relative,
            "review",
            "target Git ignore rule could not be verified",
        )

    try:
        initialize_project_memory(root)
        _write_exclusive(target, data)
    except OSError as exc:
        planned.pop(target_relative, None)
        return MigrationAction(
            source_relative, target_relative, "review", f"copy failed safely: {exc}"
        )

    return MigrationAction(source_relative, target_relative, "migrate", "copied")


def run_memory_init(repo: Path) -> int:
    root = find_repo_root(repo)
    if _is_git_ignored(root, MEMORY_RELATIVE / ".ignore-probe") is not True:
        print(
            "error: .agents/memory/ is not verifiably ignored by Git; "
            "run dotfiles install or add the ignore rule before writing memories",
            file=sys.stderr,
        )
        return 1
    try:
        memory_dir = initialize_project_memory(root)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(memory_dir)
    return 0


def run_memory_list(repo: Path, as_json: bool = False) -> int:
    root = find_repo_root(repo)
    entries = list_project_memories(root)
    if as_json:
        print(json.dumps([asdict(entry) for entry in entries], indent=2))
        return 0
    print(f"Project memories: {root / MEMORY_RELATIVE}")
    if not entries:
        print("  – no memories")
    for entry in entries:
        print(f"  {entry.name:<44} {entry.title} ({entry.lines} lines)")
    return 0


def run_memory_check(repo: Path, as_json: bool = False) -> int:
    root = find_repo_root(repo)
    statuses = check_project_memory(root)
    if as_json:
        print(
            json.dumps(
                [dict(asdict(status), ok=status.ok) for status in statuses],
                indent=2,
            )
        )
    else:
        print(f"Project memory check: {root}")
        symbols = {"ok": "✓", "info": "–", "warning": "!", "error": "✗"}
        for status in statuses:
            print(f"  {symbols[status.level]} {status.path}: {status.message}")
    return 1 if any(not status.ok for status in statuses) else 0


def run_memory_migrate(repo: Path, apply: bool = False) -> int:
    root = find_repo_root(repo)
    actions = plan_legacy_migration(root, apply=apply)
    print(f"Legacy memory migration: {root}")
    if not actions:
        print("  – no legacy memories found")
        return 0
    for action in actions:
        target = f" → {action.target}" if action.target else ""
        print(f"  {action.action:<9} {action.source}{target}: {action.message}")
    if not apply and any(action.action == "migrate" for action in actions):
        print("  Run with --apply to copy safe candidates; legacy files are retained.")
    return 1 if any(action.action == "conflict" for action in actions) else 0


def _memory_file_errors(path: Path) -> list[str]:
    try:
        byte_count = path.stat().st_size
        if byte_count > MAX_MEMORY_BYTES:
            return [f"exceeds {MAX_MEMORY_BYTES} bytes"]
        data = path.read_bytes()
        text = data.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"cannot read UTF-8 Markdown: {exc}"]
    return _memory_text_errors(path.name, text, byte_count)


def _memory_text_errors(name: str, text: str, byte_count: int) -> list[str]:
    errors: list[str] = []
    if not _MEMORY_NAME_RE.fullmatch(name):
        errors.append("filename must use lowercase hyphenated words")
    if byte_count > MAX_MEMORY_BYTES:
        errors.append(f"exceeds {MAX_MEMORY_BYTES} bytes")
    lines = text.splitlines()
    if len(lines) > MAX_MEMORY_LINES:
        errors.append(f"exceeds {MAX_MEMORY_LINES} lines")
    first_content = next((line for line in lines if line.strip()), "")
    if not first_content.startswith("# ") or not first_content[2:].strip():
        errors.append("first content line must be a level-one title")
    if "-----BEGIN " in text and "PRIVATE KEY-----" in text:
        errors.append("contains a private-key marker")
    if _SECRET_ASSIGNMENT_RE.search(text):
        errors.append("contains a possible secret assignment")
    return errors


def _migration_name(stem: str) -> str:
    stem = _DATE_PREFIX_RE.sub("", stem.lower())
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return f"{stem or 'memory-needs-review'}.md"


def _write_exclusive(target: Path, data: bytes) -> None:
    """Create *target* atomically with respect to existing paths."""
    target.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with target.open("xb") as handle:
            created = True
            handle.write(data)
    except OSError:
        # Remove only a partial regular file created by this call. Never unlink
        # a symlink or pre-existing conflict.
        if created and target.is_file() and not target.is_symlink():
            try:
                target.unlink()
            except OSError:
                pass
        raise


def _is_git_ignored(repo: Path, relative: Path) -> Optional[bool]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "check-ignore", "--quiet", "--", str(relative)],
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    return None
