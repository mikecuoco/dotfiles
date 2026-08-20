"""Tests for agent skill metadata parsing and health reporting.

Installation is chezmoi's job — see tests/test_chezmoi_render.py. What is
covered here is the frontmatter contract both Claude Code and Codex rely on,
and the status reporting `dotfiles doctor` builds on top of it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dotfiles.agent_skills import (
    SkillMetadata,
    _parse_skill_metadata_text,
    check_skill_statuses,
)


def _skill(target: Path, name: str, frontmatter: str) -> Path:
    """Write an installed skill directory called *name*."""
    skill = target / name
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(frontmatter, encoding="utf-8")
    return skill


def _valid(name: str) -> str:
    return f"---\nname: {name}\ndescription: Does a thing.\n---\n\nBody.\n"


# ── Frontmatter parsing ───────────────────────────────────────────────────────

def test_parses_plain_scalars():
    meta = _parse_skill_metadata_text(_valid("example-skill"))
    assert meta == SkillMetadata(name="example-skill", description="Does a thing.")


@pytest.mark.parametrize("quoted", ['"Quoted value."', "'Quoted value.'"])
def test_parses_quoted_descriptions(quoted):
    text = f"---\nname: example\ndescription: {quoted}\n---\n"
    assert _parse_skill_metadata_text(text).description == "Quoted value."


def test_parses_literal_block_scalar():
    text = "---\nname: example\ndescription: |\n  First line.\n  Second line.\n---\n"
    assert _parse_skill_metadata_text(text).description == "First line.\nSecond line."


def test_parses_folded_block_scalar():
    text = "---\nname: example\ndescription: >\n  First line.\n  Second line.\n---\n"
    assert _parse_skill_metadata_text(text).description == "First line. Second line."


def test_ignores_unrelated_frontmatter_keys():
    """Codex-specific keys must not confuse the portable parser."""
    text = (
        "---\nname: example\ntool_type: cli\n"
        "description: Does a thing.\nprimary_tool: samtools\n---\n"
    )
    meta = _parse_skill_metadata_text(text)
    assert meta.name == "example"
    assert meta.description == "Does a thing."


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
        _parse_skill_metadata_text(text)


# ── Status reporting (used by doctor) ─────────────────────────────────────────

def test_empty_when_directory_missing(tmp_path):
    assert check_skill_statuses(tmp_path / "nope") == []


def test_empty_for_empty_directory(tmp_path):
    (tmp_path / "skills").mkdir()
    assert check_skill_statuses(tmp_path / "skills") == []


def test_reports_installed_skills(tmp_path):
    _skill(tmp_path, "alpha", _valid("alpha"))
    _skill(tmp_path, "beta", _valid("beta"))
    statuses = check_skill_statuses(tmp_path)
    assert [s.name for s in statuses] == ["alpha", "beta"]
    assert all(s.installed and s.category == "first-party" for s in statuses)


def test_flags_metadata_name_not_matching_its_directory(tmp_path):
    """A mismatch stops the agent loading the skill, so it is not 'installed'."""
    _skill(tmp_path, "alpha", _valid("something-else"))
    status = check_skill_statuses(tmp_path)[0]
    assert status.installed is False
    assert "does not match directory" in status.message


def test_flags_unparseable_skill(tmp_path):
    _skill(tmp_path, "alpha", "no frontmatter\n")
    status = check_skill_statuses(tmp_path)[0]
    assert status.installed is False
    assert "invalid skill" in status.message


def test_ignores_directories_without_a_skill_file(tmp_path):
    (tmp_path / "not-a-skill").mkdir()
    _skill(tmp_path, "alpha", _valid("alpha"))
    assert [s.name for s in check_skill_statuses(tmp_path)] == ["alpha"]
