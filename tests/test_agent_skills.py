"""Tests for the agent skill frontmatter contract.

Installation is chezmoi's job — see tests/test_chezmoi_render.py. What is
covered here is the `SKILL.md` frontmatter contract that both Claude Code and
Codex rely on, asserted against the skills actually checked into `home/`.

A skill whose `name` is missing, malformed, or disagrees with its directory is
silently not loaded by either agent, which is exactly the kind of failure a test
should catch rather than a per-machine health command: the source is the same
everywhere, so this is a repository invariant.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import REPO_ROOT

SKILLS_DIR = REPO_ROOT / "home" / "dot_claude" / "skills"

#: Both agents require a lowercase, hyphenated, filesystem-safe name.
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_skill_metadata(text: str) -> tuple[str, str]:
    """Return (name, description) from a SKILL.md, or raise ValueError.

    A deliberately small YAML subset — the portable frontmatter format shared by
    Claude Code and Codex: plain scalars, single/double-quoted scalars, and
    literal (`|`) or folded (`>`, `>-`) block scalars. Unrelated keys are
    ignored, since Codex adds its own (`tool_type`, `primary_tool`).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise ValueError("missing YAML frontmatter") from None

    fields: dict[str, str] = {}
    i = 1
    while i < end:
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if value.startswith(("|", ">")):
            folded = value.startswith(">")
            block: list[str] = []
            while i < end and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                block.append(lines[i].strip())
                i += 1
            joined = " ".join(b for b in block if b) if folded else "\n".join(block)
            fields[key] = joined.strip()
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key] = value

    name = fields.get("name", "")
    description = fields.get("description", "")
    if not name:
        raise ValueError("missing skill name")
    if not description:
        raise ValueError("missing skill description")
    if not NAME_RE.match(name):
        raise ValueError(f"invalid skill name: {name!r}")
    return name, description


# ── Frontmatter parsing ───────────────────────────────────────────────────────

def test_parses_plain_scalars():
    text = "---\nname: example-skill\ndescription: Does a thing.\n---\n\nBody.\n"
    assert parse_skill_metadata(text) == ("example-skill", "Does a thing.")


@pytest.mark.parametrize("quoted", ['"Quoted value."', "'Quoted value.'"])
def test_parses_quoted_descriptions(quoted):
    text = f"---\nname: example\ndescription: {quoted}\n---\n"
    assert parse_skill_metadata(text)[1] == "Quoted value."


def test_parses_literal_block_scalar():
    text = "---\nname: example\ndescription: |\n  First line.\n  Second line.\n---\n"
    assert parse_skill_metadata(text)[1] == "First line.\nSecond line."


def test_parses_folded_block_scalar():
    text = "---\nname: example\ndescription: >\n  First line.\n  Second line.\n---\n"
    assert parse_skill_metadata(text)[1] == "First line. Second line."


def test_parses_stripped_folded_block_scalar():
    """`>-` is what the bundled brisc skill actually uses."""
    text = "---\nname: example\ndescription: >-\n  First line.\n  Second line.\n---\n"
    assert parse_skill_metadata(text)[1] == "First line. Second line."


def test_ignores_unrelated_frontmatter_keys():
    """Codex-specific keys must not confuse the portable parser."""
    text = (
        "---\nname: example\ntool_type: cli\n"
        "description: Does a thing.\nprimary_tool: samtools\n---\n"
    )
    assert parse_skill_metadata(text) == ("example", "Does a thing.")


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("no frontmatter at all\n", "missing YAML frontmatter"),
        ("---\ndescription: d\n---\n", "missing skill name"),
        ("---\nname: example\n---\n", "missing skill description"),
        ("---\nname: Bad Name\ndescription: d\n---\n", "invalid skill name"),
    ],
)
def test_rejects_malformed_metadata(text, reason):
    with pytest.raises(ValueError, match=reason):
        parse_skill_metadata(text)


# ── The skills actually shipped in home/ ──────────────────────────────────────

def _bundled_skills() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").is_file())


def test_repository_ships_skills():
    """Guard against the glob silently going empty after a move."""
    assert _bundled_skills(), f"no SKILL.md found under {SKILLS_DIR}"


@pytest.mark.parametrize(
    "skill", _bundled_skills(), ids=lambda p: p.name
)
def test_bundled_skill_frontmatter_is_valid(skill):
    """Every shipped skill parses and its name matches its directory."""
    name, description = parse_skill_metadata(
        (skill / "SKILL.md").read_text(encoding="utf-8")
    )
    assert name == skill.name, (
        f"{skill.name}/SKILL.md declares name {name!r}; a mismatch means neither "
        "Claude Code nor Codex will load the skill."
    )
    assert description.strip(), f"{skill.name} has an empty description"


def test_bundled_skill_names_are_unique():
    names = [p.name for p in _bundled_skills()]
    assert len(names) == len(set(names))
