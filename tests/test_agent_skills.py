"""Tests for GPTomics bioSkills management.

First-party skills are no longer handled here: they live in the chezmoi source
at home/dot_claude/skills/ and are covered by tests/test_chezmoi_render.py.

All git calls are mocked so these run without network access.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dotfiles import RESOURCES_DIR
from dotfiles.agent_skills import (
    SkillsConfig,
    _discover_skills,
    _should_link,
    check_skill_statuses,
    load_skills_config,
    run_skills_setup,
)

RESOURCES = RESOURCES_DIR


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_completed(returncode=0, stdout="", stderr=""):
    m = MagicMock(spec=subprocess.CompletedProcess)
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def _fake_repo(tmp_path: Path, entries, extra=None) -> Path:
    """Build a fake bioSkills clone.

    *entries* is a list of (category, dir_name, declared_name) tuples; the
    declared name may deliberately differ from the directory name, which is
    what upstream does for 143 of its skills.
    """
    cache = tmp_path / "bioskills"
    (cache / ".git").mkdir(parents=True, exist_ok=True)
    for category, dir_name, declared in entries:
        skill = cache / category / dir_name
        skill.mkdir(parents=True, exist_ok=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {declared}\ndescription: Test {declared}\n---\n\nBody.\n",
            encoding="utf-8",
        )
        for rel, text in (extra or {}).items():
            path = skill / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    return cache


def _config(tmp_path: Path, categories) -> Path:
    """A resources tree whose skills.toml selects *categories*."""
    resources = tmp_path / "resources" / "agents"
    resources.mkdir(parents=True, exist_ok=True)
    cats = ", ".join(f'"{c}"' for c in categories)
    # categories must precede [repo]: a bare key after a table header belongs
    # to that table, which is exactly the bug this ordering guards against.
    (resources / "skills.toml").write_text(
        f'categories = [{cats}]\n\n[repo]\nurl = "https://example.invalid/repo"\n'
    )
    return tmp_path / "resources"


# ── Config ────────────────────────────────────────────────────────────────────

def test_shipped_config_parses():
    config = load_skills_config(RESOURCES)
    assert isinstance(config, SkillsConfig)


def test_shipped_config_points_at_gptomics():
    assert "GPTomics/bioSkills" in load_skills_config(RESOURCES).repo_url


def test_shipped_config_installs_every_category_by_default():
    """An empty category list means no filter."""
    assert load_skills_config(RESOURCES).categories == []


def test_categories_round_trip(tmp_path):
    resources = _config(tmp_path, ["read-qc", "single-cell"])
    assert load_skills_config(resources).categories == ["read-qc", "single-cell"]


# ── Discovery ─────────────────────────────────────────────────────────────────

def test_discovery_uses_the_declared_name_not_the_path(tmp_path):
    """Upstream de-duplicates the category word; honour what it declares."""
    cache = _fake_repo(tmp_path, [("alignment", "alignment-io", "bio-alignment-io")])
    found = _discover_skills(cache, [])
    assert [s.installed_name for s in found] == ["bio-alignment-io"]
    assert found[0].category == "alignment"
    assert found[0].source.name == "alignment-io"


def test_discovery_filters_by_category(tmp_path):
    cache = _fake_repo(tmp_path, [
        ("read-qc", "trimming", "bio-read-qc-trimming"),
        ("spatial", "visium", "bio-spatial-visium"),
    ])
    assert [s.installed_name for s in _discover_skills(cache, ["read-qc"])] == [
        "bio-read-qc-trimming"
    ]


def test_discovery_with_no_filter_returns_everything(tmp_path):
    cache = _fake_repo(tmp_path, [
        ("read-qc", "trimming", "bio-read-qc-trimming"),
        ("spatial", "visium", "bio-spatial-visium"),
    ])
    assert len(_discover_skills(cache, [])) == 2


def test_discovery_ignores_wrong_depth_files(tmp_path):
    """Repository furniture at the wrong depth is not a skill."""
    cache = _fake_repo(tmp_path, [("read-qc", "trimming", "bio-read-qc-trimming")])
    (cache / "SKILL.md").write_text("---\nname: stray\ndescription: d\n---\n")
    deep = cache / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "SKILL.md").write_text("---\nname: deep\ndescription: d\n---\n")
    assert [s.installed_name for s in _discover_skills(cache, [])] == [
        "bio-read-qc-trimming"
    ]


def test_discovery_skips_duplicate_declared_names(tmp_path):
    """Two skills cannot claim the same install directory."""
    cache = _fake_repo(tmp_path, [
        ("cat-a", "one", "bio-clash"),
        ("cat-b", "two", "bio-clash"),
    ])
    assert len(_discover_skills(cache, [])) == 1


def test_discovery_skips_unparseable_metadata(tmp_path):
    cache = _fake_repo(tmp_path, [("read-qc", "ok", "bio-read-qc-ok")])
    broken = cache / "read-qc" / "broken"
    broken.mkdir()
    (broken / "SKILL.md").write_text("no frontmatter here\n")
    assert [s.installed_name for s in _discover_skills(cache, [])] == ["bio-read-qc-ok"]


# ── Link vs copy ──────────────────────────────────────────────────────────────

def test_targets_outside_the_capsule_are_linked(tmp_path, monkeypatch):
    monkeypatch.setenv("DOTFILES_CAPSULE_DIR", str(tmp_path / "capsule"))
    assert _should_link(tmp_path / "home" / ".claude" / "skills") is True


def test_targets_inside_the_capsule_are_copied(tmp_path, monkeypatch):
    """Capsule contents outlive any clone of the cache, so links would dangle."""
    capsule = tmp_path / "capsule"
    (capsule / ".claude" / "skills").mkdir(parents=True)
    monkeypatch.setenv("DOTFILES_CAPSULE_DIR", str(capsule))
    assert _should_link(capsule / ".claude" / "skills") is False


# ── Installation ──────────────────────────────────────────────────────────────

@pytest.fixture()
def installed(tmp_path):
    """A repo with two skills installed as symlinks into the cache."""
    cache = _fake_repo(
        tmp_path,
        [("read-qc", "trimming", "bio-read-qc-trimming"),
         ("spatial", "visium", "bio-spatial-visium")],
        extra={"usage-guide.md": "guide\n", "examples/demo.txt": "demo\n"},
    )
    resources = _config(tmp_path, [])
    target = tmp_path / "skills"
    statuses = run_skills_setup(
        resources_dir=resources, cache_dir=cache, target_dir=target, link=True
    )
    return cache, resources, target, statuses


def test_install_creates_one_entry_per_skill(installed):
    _, _, target, statuses = installed
    assert sorted(p.name for p in target.iterdir()) == [
        "bio-read-qc-trimming", "bio-spatial-visium"
    ]
    assert all(s.installed for s in statuses)


def test_install_preserves_supporting_files(installed):
    """A skill is a directory: usage guides and examples come with it."""
    _, _, target, _ = installed
    skill = target / "bio-read-qc-trimming"
    assert (skill / "SKILL.md").is_file()
    assert (skill / "usage-guide.md").read_text() == "guide\n"
    assert (skill / "examples" / "demo.txt").read_text() == "demo\n"


def test_install_is_idempotent(installed):
    cache, resources, target, _ = installed
    again = run_skills_setup(
        resources_dir=resources, cache_dir=cache, target_dir=target, link=True
    )
    assert {s.message for s in again} == {"unchanged"}


def test_copy_mode_produces_real_directories(tmp_path):
    cache = _fake_repo(tmp_path, [("read-qc", "trimming", "bio-read-qc-trimming")],
                       extra={"usage-guide.md": "guide\n"})
    resources = _config(tmp_path, [])
    target = tmp_path / "skills"
    run_skills_setup(resources_dir=resources, cache_dir=cache,
                     target_dir=target, link=False)
    skill = target / "bio-read-qc-trimming"
    assert skill.is_dir() and not skill.is_symlink()
    assert (skill / "usage-guide.md").read_text() == "guide\n"


def test_copy_mode_is_idempotent(tmp_path):
    cache = _fake_repo(tmp_path, [("read-qc", "trimming", "bio-read-qc-trimming")])
    resources = _config(tmp_path, [])
    target = tmp_path / "skills"
    kwargs = dict(resources_dir=resources, cache_dir=cache,
                  target_dir=target, link=False)
    run_skills_setup(**kwargs)
    assert {s.message for s in run_skills_setup(**kwargs)} == {"unchanged"}


def test_switching_from_link_to_copy_replaces_the_entry(tmp_path):
    cache = _fake_repo(tmp_path, [("read-qc", "trimming", "bio-read-qc-trimming")])
    resources = _config(tmp_path, [])
    target = tmp_path / "skills"
    run_skills_setup(resources_dir=resources, cache_dir=cache,
                     target_dir=target, link=True)
    assert (target / "bio-read-qc-trimming").is_symlink()
    run_skills_setup(resources_dir=resources, cache_dir=cache,
                     target_dir=target, link=False)
    assert not (target / "bio-read-qc-trimming").is_symlink()


# ── Pruning ───────────────────────────────────────────────────────────────────

def test_narrowing_categories_removes_deselected_skills(installed):
    """This is what makes the category list meaningful rather than additive."""
    cache, _, target, _ = installed
    narrowed = _config(target.parent / "narrowed", ["read-qc"])
    run_skills_setup(resources_dir=narrowed, cache_dir=cache,
                     target_dir=target, link=True)
    assert sorted(p.name for p in target.iterdir()) == ["bio-read-qc-trimming"]


def test_pruning_leaves_non_bio_skills_alone(installed):
    """First-party and hand-made skills are outside the managed namespace."""
    cache, _, target, _ = installed
    (target / "my-own-skill").mkdir()
    (target / "my-own-skill" / "SKILL.md").write_text("---\nname: x\n---\n")
    narrowed = _config(target.parent / "narrowed", ["read-qc"])
    run_skills_setup(resources_dir=narrowed, cache_dir=cache,
                     target_dir=target, link=True)
    assert (target / "my-own-skill" / "SKILL.md").exists()


# ── git handling ──────────────────────────────────────────────────────────────

def test_dry_run_makes_no_git_calls_and_no_writes(tmp_path, capsys):
    resources = _config(tmp_path, [])
    target = tmp_path / "skills"
    with patch("dotfiles.agent_skills._run_git") as git:
        run_skills_setup(resources_dir=resources, cache_dir=tmp_path / "cache",
                         target_dir=target, dry_run=True)
    git.assert_not_called()
    assert not target.exists()
    assert "[dry]" in capsys.readouterr().out


def test_first_run_clones(tmp_path):
    resources = _config(tmp_path, [])
    with patch("dotfiles.agent_skills._run_git",
               return_value=_make_completed()) as git:
        run_skills_setup(resources_dir=resources, cache_dir=tmp_path / "cache",
                         target_dir=tmp_path / "skills")
    assert git.call_args[0][0][0] == "clone"


def test_install_does_not_pull_an_existing_clone(tmp_path):
    """`dotfiles install` runs often; only `update` should hit the network."""
    cache = _fake_repo(tmp_path, [("read-qc", "trimming", "bio-read-qc-trimming")])
    resources = _config(tmp_path, [])
    with patch("dotfiles.agent_skills._run_git",
               return_value=_make_completed()) as git:
        run_skills_setup(resources_dir=resources, cache_dir=cache,
                         target_dir=tmp_path / "skills", update=False)
    git.assert_not_called()


def test_update_pulls_an_existing_clone(tmp_path):
    cache = _fake_repo(tmp_path, [("read-qc", "trimming", "bio-read-qc-trimming")])
    resources = _config(tmp_path, [])
    with patch("dotfiles.agent_skills._run_git",
               return_value=_make_completed()) as git:
        run_skills_setup(resources_dir=resources, cache_dir=cache,
                         target_dir=tmp_path / "skills", update=True)
    assert "pull" in git.call_args[0][0]


def test_clone_failure_is_reported_not_raised(tmp_path, capsys):
    resources = _config(tmp_path, [])
    with patch("dotfiles.agent_skills._run_git",
               return_value=_make_completed(returncode=1, stderr="boom")):
        statuses = run_skills_setup(resources_dir=resources,
                                    cache_dir=tmp_path / "cache",
                                    target_dir=tmp_path / "skills")
    assert statuses == []
    assert "failed" in capsys.readouterr().err


def test_missing_git_is_reported_not_raised(tmp_path, capsys):
    resources = _config(tmp_path, [])
    with patch("dotfiles.agent_skills.shutil.which", return_value=None):
        statuses = run_skills_setup(resources_dir=resources,
                                    cache_dir=tmp_path / "cache",
                                    target_dir=tmp_path / "skills")
    assert statuses == []
    assert "git not found" in capsys.readouterr().err


# ── Status reporting (used by doctor) ─────────────────────────────────────────

def test_check_statuses_empty_when_dir_missing(tmp_path):
    assert check_skill_statuses(tmp_path / "nope") == []


def test_check_statuses_empty_for_empty_dir(tmp_path):
    tmp_path.joinpath("skills").mkdir()
    assert check_skill_statuses(tmp_path / "skills") == []


def test_check_statuses_separates_bio_from_first_party(installed):
    _, _, target, _ = installed
    (target / "my-own-skill").mkdir()
    (target / "my-own-skill" / "SKILL.md").write_text(
        "---\nname: my-own-skill\ndescription: d\n---\n"
    )
    by_category = {}
    for status in check_skill_statuses(target):
        by_category.setdefault(status.category, []).append(status.name)
    assert sorted(by_category["bioinformatics"]) == [
        "bio-read-qc-trimming", "bio-spatial-visium"
    ]
    assert by_category["first-party"] == ["my-own-skill"]
