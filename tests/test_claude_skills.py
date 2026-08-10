"""Tests for GPTomics bioSkills management.

All subprocess calls (git) and filesystem writes are mocked so these tests run
without network access or a live bioSkills installation.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from dotfiles.claude_skills import (
    SkillStatus,
    SkillsConfig,
    check_skill_statuses,
    load_skills_config,
    run_skills_setup,
)
from dotfiles.install import get_resources_dir

RESOURCES = get_resources_dir()


# ── Config loading ─────────────────────────────────────────────────────────────

def test_config_loads_without_error():
    """skills.toml parses without exception."""
    cfg = load_skills_config(RESOURCES)
    assert isinstance(cfg, SkillsConfig)
    assert cfg.repo_url
    assert cfg.groups


def test_repo_url_is_gptomics():
    cfg = load_skills_config(RESOURCES)
    assert "GPTomics" in cfg.repo_url or "gptomics" in cfg.repo_url.lower()


def test_default_group_exists():
    cfg = load_skills_config(RESOURCES)
    assert "default" in cfg.groups


def test_spatial_group_exists():
    cfg = load_skills_config(RESOURCES)
    assert "spatial" in cfg.groups


def test_genomics_group_exists():
    cfg = load_skills_config(RESOURCES)
    assert "genomics" in cfg.groups


def test_all_group_exists():
    cfg = load_skills_config(RESOURCES)
    assert "all" in cfg.groups


def test_all_group_has_empty_categories():
    """The 'all' group uses an empty category list as the 'install everything' signal."""
    cfg = load_skills_config(RESOURCES)
    assert cfg.groups["all"].categories == []


def test_default_group_contains_core_categories():
    cfg = load_skills_config(RESOURCES)
    categories = cfg.groups["default"].categories
    assert "single-cell" in categories
    assert "read-qc" in categories
    assert "differential-expression" in categories


def test_spatial_group_contains_spatial_transcriptomics():
    cfg = load_skills_config(RESOURCES)
    assert "spatial-transcriptomics" in cfg.groups["spatial"].categories


def test_all_groups_have_descriptions():
    cfg = load_skills_config(RESOURCES)
    for name, group in cfg.groups.items():
        assert group.description, f"Group {name!r} has no description"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_completed(returncode=0, stdout="", stderr=""):
    m = MagicMock(spec=subprocess.CompletedProcess)
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def _fake_skill_tree(tmp_path: Path, entries: list[tuple[str, str, str]]) -> Path:
    """Create a fake bioSkills repo layout and return the root path.

    *entries* is a list of (category, skill_name, content) tuples.
    """
    cache = tmp_path / "bioskills"
    (cache / ".git").mkdir(parents=True)  # marks it as a cloned repo
    for category, skill_name, content in entries:
        skill_dir = cache / category / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return cache


# ── run_skills_setup — dry run ────────────────────────────────────────────────

def test_dry_run_makes_no_git_calls(tmp_path, capsys):
    """In dry-run mode, no git subprocess calls are made."""
    target = tmp_path / "skills"
    cache  = tmp_path / "cache"

    with patch("dotfiles.claude_skills._run_git") as mock_git, \
         patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"):
        run_skills_setup(
            RESOURCES,
            groups=["default"],
            cache_dir=cache,
            target_dir=target,
            dry_run=True,
        )

    assert mock_git.call_count == 0, "dry-run must not call git"


def test_dry_run_makes_no_file_writes(tmp_path, capsys):
    """In dry-run mode, target directory is not created or written to."""
    target = tmp_path / "skills"
    cache  = tmp_path / "cache"

    with patch("dotfiles.claude_skills._run_git"), \
         patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"):
        run_skills_setup(
            RESOURCES,
            groups=["default"],
            cache_dir=cache,
            target_dir=target,
            dry_run=True,
        )

    assert not target.exists(), "dry-run must not create target directory"


def test_dry_run_output_mentions_dry(capsys, tmp_path):
    target = tmp_path / "skills"
    cache  = tmp_path / "cache"

    with patch("dotfiles.claude_skills._run_git"), \
         patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"):
        run_skills_setup(
            RESOURCES,
            groups=["default"],
            cache_dir=cache,
            target_dir=target,
            dry_run=True,
        )

    out = capsys.readouterr().out
    assert "[dry]" in out


# ── run_skills_setup — git clone on first run ─────────────────────────────────

def test_first_run_clones_repo(tmp_path):
    """When the cache dir has no .git, a clone is attempted."""
    cache  = tmp_path / "bioskills"       # does NOT exist yet
    target = tmp_path / "skills"

    with patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"), \
         patch("dotfiles.claude_skills._run_git", return_value=_make_completed()) as mock_git, \
         patch("dotfiles.claude_skills._discover_skills", return_value=[]):
        run_skills_setup(RESOURCES, groups=["default"], cache_dir=cache, target_dir=target)

    clone_calls = [
        c for c in mock_git.call_args_list
        if c.args[0][0] == "clone"
    ]
    assert len(clone_calls) == 1
    assert any("GPTomics/bioSkills" in arg for arg in clone_calls[0].args[0])


def test_subsequent_run_pulls_not_clones(tmp_path):
    """When the cache dir already has .git, a pull is attempted instead of clone."""
    cache  = _fake_skill_tree(tmp_path, [])
    target = tmp_path / "skills"

    with patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"), \
         patch("dotfiles.claude_skills._run_git", return_value=_make_completed()) as mock_git, \
         patch("dotfiles.claude_skills._discover_skills", return_value=[]):
        run_skills_setup(RESOURCES, groups=["default"], cache_dir=cache, target_dir=target)

    clone_calls = [c for c in mock_git.call_args_list if c.args[0][0] == "clone"]
    pull_calls  = [c for c in mock_git.call_args_list if "pull" in c.args[0]]
    assert clone_calls == [], "Should not clone when repo already exists"
    assert pull_calls, "Should pull when repo already exists"


# ── run_skills_setup — file copying ──────────────────────────────────────────

def test_skills_copied_with_correct_names(tmp_path):
    """SKILL.md files are copied as bio-<category>-<skill>.md."""
    cache = _fake_skill_tree(tmp_path, [
        ("single-cell", "clustering", "# clustering skill"),
        ("read-qc", "fastp-workflow", "# fastp skill"),
    ])
    target = tmp_path / "skills"

    with patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"), \
         patch("dotfiles.claude_skills._run_git", return_value=_make_completed()):
        run_skills_setup(
            RESOURCES,
            groups=["default"],
            cache_dir=cache,
            target_dir=target,
        )

    assert (target / "bio-single-cell-clustering.md").exists()
    assert (target / "bio-read-qc-fastp-workflow.md").exists()


def test_skill_content_is_preserved(tmp_path):
    """Content of SKILL.md is faithfully copied to the target."""
    content = "# My Skill\nThis is the skill content."
    cache = _fake_skill_tree(tmp_path, [("single-cell", "clustering", content)])
    target = tmp_path / "skills"

    with patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"), \
         patch("dotfiles.claude_skills._run_git", return_value=_make_completed()):
        run_skills_setup(
            RESOURCES,
            groups=["default"],
            cache_dir=cache,
            target_dir=target,
        )

    written = (target / "bio-single-cell-clustering.md").read_text()
    assert written == content


# ── run_skills_setup — idempotency ───────────────────────────────────────────

def test_unchanged_skills_not_rewritten(tmp_path):
    """If a skill file already exists with identical content, it is skipped."""
    content = "# clustering"
    cache = _fake_skill_tree(tmp_path, [("single-cell", "clustering", content)])
    target = tmp_path / "skills"
    target.mkdir()
    dest = target / "bio-single-cell-clustering.md"
    dest.write_text(content)
    mtime_before = dest.stat().st_mtime_ns

    with patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"), \
         patch("dotfiles.claude_skills._run_git", return_value=_make_completed()):
        statuses = run_skills_setup(
            RESOURCES,
            groups=["default"],
            cache_dir=cache,
            target_dir=target,
        )

    clustering = next(s for s in statuses if "clustering" in s.name)
    assert clustering.installed
    assert clustering.message == "already installed"
    assert dest.stat().st_mtime_ns == mtime_before, "Unchanged file must not be rewritten"


def test_changed_skill_is_updated(tmp_path):
    """If a skill file has new content (after a pull), it is overwritten."""
    cache = _fake_skill_tree(tmp_path, [("single-cell", "clustering", "# new content")])
    target = tmp_path / "skills"
    target.mkdir()
    dest = target / "bio-single-cell-clustering.md"
    dest.write_text("# old content")

    with patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"), \
         patch("dotfiles.claude_skills._run_git", return_value=_make_completed()):
        statuses = run_skills_setup(
            RESOURCES,
            groups=["default"],
            cache_dir=cache,
            target_dir=target,
        )

    clustering = next(s for s in statuses if "clustering" in s.name)
    assert clustering.message == "updated"
    assert dest.read_text() == "# new content"


# ── run_skills_setup — category filtering ────────────────────────────────────

def test_only_requested_categories_are_installed(tmp_path):
    """Skills outside the requested category list are not copied."""
    cache = _fake_skill_tree(tmp_path, [
        ("single-cell", "clustering", "# clustering"),
        ("variant-calling", "gatk", "# gatk"),
    ])
    target = tmp_path / "skills"

    # Only install "single-cell" (via a minimal group)
    with patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"), \
         patch("dotfiles.claude_skills._run_git", return_value=_make_completed()):
        statuses = run_skills_setup(
            RESOURCES,
            groups=["default"],   # default includes single-cell but NOT variant-calling
            cache_dir=cache,
            target_dir=target,
        )

    names = {s.name for s in statuses}
    assert "bio-single-cell-clustering.md" in names
    assert "bio-variant-calling-gatk.md" not in names


def test_all_group_installs_all_categories(tmp_path):
    """The 'all' group (empty categories list) installs skills from every category."""
    cache = _fake_skill_tree(tmp_path, [
        ("single-cell", "clustering", "# clustering"),
        ("variant-calling", "gatk", "# gatk"),
        ("metagenomics", "kraken", "# kraken"),
    ])
    target = tmp_path / "skills"

    with patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"), \
         patch("dotfiles.claude_skills._run_git", return_value=_make_completed()):
        statuses = run_skills_setup(
            RESOURCES,
            groups=["all"],
            cache_dir=cache,
            target_dir=target,
        )

    names = {s.name for s in statuses}
    assert "bio-single-cell-clustering.md" in names
    assert "bio-variant-calling-gatk.md" in names
    assert "bio-metagenomics-kraken.md" in names


# ── run_skills_setup — error handling ────────────────────────────────────────

def test_git_not_on_path_returns_empty(tmp_path, capsys):
    cache  = tmp_path / "cache"
    target = tmp_path / "skills"

    with patch("dotfiles.claude_skills.shutil.which", return_value=None):
        result = run_skills_setup(
            RESOURCES, groups=["default"], cache_dir=cache, target_dir=target
        )

    assert result == []
    assert "git not found" in capsys.readouterr().err


def test_git_clone_failure_returns_empty(tmp_path, capsys):
    cache  = tmp_path / "cache"
    target = tmp_path / "skills"

    with patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"), \
         patch("dotfiles.claude_skills._run_git",
               return_value=_make_completed(returncode=1, stderr="fatal: repo not found")):
        result = run_skills_setup(
            RESOURCES, groups=["default"], cache_dir=cache, target_dir=target
        )

    assert result == []
    assert "git clone failed" in capsys.readouterr().err


def test_unknown_group_warns_and_continues(tmp_path, capsys):
    cache  = _fake_skill_tree(tmp_path, [])
    target = tmp_path / "skills"

    with patch("dotfiles.claude_skills.shutil.which", return_value="/usr/bin/git"), \
         patch("dotfiles.claude_skills._run_git", return_value=_make_completed()):
        result = run_skills_setup(
            RESOURCES,
            groups=["nonexistent-group"],
            cache_dir=cache,
            target_dir=target,
        )

    assert isinstance(result, list)
    assert "unknown skills group" in capsys.readouterr().err


# ── check_skill_statuses (read-only, used by doctor) ─────────────────────────

def test_check_statuses_empty_when_dir_missing(tmp_path):
    target = tmp_path / "skills"  # does not exist
    result = check_skill_statuses(target)
    assert result == []


def test_check_statuses_counts_bio_files(tmp_path):
    target = tmp_path / "skills"
    target.mkdir()
    (target / "bio-single-cell-clustering.md").write_text("x")
    (target / "bio-read-qc-fastp-workflow.md").write_text("x")
    (target / "something-else.md").write_text("x")  # not a bio-* file, should be ignored

    result = check_skill_statuses(target)
    assert len(result) == 2
    assert all(s.installed for s in result)


def test_check_statuses_derives_category(tmp_path):
    target = tmp_path / "skills"
    target.mkdir()
    (target / "bio-single-cell-clustering.md").write_text("x")

    result = check_skill_statuses(target)
    assert len(result) == 1
    assert result[0].category == "single"   # "bio-single-cell-clustering" → parts[1]


def test_check_statuses_does_not_raise_on_empty_dir(tmp_path):
    target = tmp_path / "skills"
    target.mkdir()
    result = check_skill_statuses(target)
    assert result == []
