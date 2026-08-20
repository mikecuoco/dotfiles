"""Agent skill metadata and health reporting.

Skills themselves are ordinary managed files: they live in the chezmoi source
at ``home/dot_claude/skills/`` and install with everything else, with
``~/.agents/skills`` symlinked to the same tree so Codex reads it too.

What remains here is the part chezmoi has no opinion about -- parsing the
portable Agent Skills frontmatter and reporting whether what is installed is
valid. ``dotfiles doctor`` is the only consumer.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


_SKILL_NAME_RE = re.compile(r"[a-z0-9-]{1,64}")
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---(?:\s*\n|\Z)", re.DOTALL)


@dataclass
class SkillStatus:
    """Result of installing or checking one skill."""

    name: str           # the skill's directory name
    category: str       # provenance, e.g. "first-party"
    installed: bool
    message: str        # "installed", or why it is not usable


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

# ── Status reporting ─────────────────────────────────────────────────────────

def check_skill_statuses(target_dir: Optional[Path] = None) -> list[SkillStatus]:
    """Return a status for every installed skill.

    Used by ``dotfiles doctor``.  Never raises; returns an empty list when the
    target directory does not exist.
    """
    if target_dir is None:
        target_dir = Path.home() / ".claude" / "skills"

    if not target_dir.exists():
        return []

    return [
        _installed_status(skill_file.parent.name, skill_file, "first-party")
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
