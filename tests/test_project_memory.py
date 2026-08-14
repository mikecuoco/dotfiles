"""Tests for the shared .agents/memory/ project convention."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dotfiles.project_memory import (
    MEMORY_RELATIVE,
    check_project_memory,
    find_repo_root,
    initialize_project_memory,
    list_project_memories,
    plan_legacy_migration,
    run_memory_check,
    run_memory_init,
    run_memory_list,
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    return repo


def _write_memory(repo: Path, name: str, text: str) -> Path:
    memory_dir = initialize_project_memory(repo)
    path = memory_dir / name
    path.write_text(text, encoding="utf-8")
    return path


def test_find_repo_root_walks_up_from_nested_directory(tmp_path):
    repo = _repo(tmp_path)
    nested = repo / "src" / "package"
    nested.mkdir(parents=True)

    assert find_repo_root(nested) == repo


def test_initialize_creates_singular_memory_directory(tmp_path):
    repo = _repo(tmp_path)

    memory_dir = initialize_project_memory(repo)

    assert memory_dir == repo / MEMORY_RELATIVE
    assert memory_dir.is_dir()
    assert not (repo / ".agents" / "memories").exists()


def test_initialize_refuses_symlinked_agents_directory(tmp_path):
    repo = _repo(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (repo / ".agents").symlink_to(elsewhere, target_is_directory=True)

    with pytest.raises(OSError, match="refusing .agents"):
        initialize_project_memory(repo)


def test_init_command_refuses_unverified_ignore_rule(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    monkeypatch.setattr("dotfiles.project_memory._is_git_ignored", lambda *args: False)

    assert run_memory_init(repo) == 1

    assert "not verifiably ignored" in capsys.readouterr().err
    assert not (repo / MEMORY_RELATIVE).exists()


def test_list_reports_names_titles_and_lines_only(tmp_path):
    repo = _repo(tmp_path)
    _write_memory(repo, "redis-tests.md", "# Redis tests\n\nUse REDIS_URL.\n")
    _write_memory(repo, "ignored.txt", "not a memory")

    entries = list_project_memories(repo)

    assert len(entries) == 1
    assert entries[0].name == "redis-tests.md"
    assert entries[0].title == "Redis tests"
    assert entries[0].lines == 3


def test_check_accepts_valid_ignored_memory(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    _write_memory(repo, "redis-tests.md", "# Redis tests\n\nUse REDIS_URL.\n")
    monkeypatch.setattr("dotfiles.project_memory._is_git_ignored", lambda *args: True)

    statuses = check_project_memory(repo)

    assert all(status.ok for status in statuses)
    assert any(status.message == "valid memory" for status in statuses)


def test_check_reports_uninitialized_directory_as_informational(tmp_path):
    repo = _repo(tmp_path)

    statuses = check_project_memory(repo)

    assert statuses[0].level == "info"
    assert statuses[0].message == "not initialized"


def test_check_rejects_unignored_directory(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    initialize_project_memory(repo)
    monkeypatch.setattr("dotfiles.project_memory._is_git_ignored", lambda *args: False)

    statuses = check_project_memory(repo)

    assert any(not status.ok and status.message == "not ignored by Git" for status in statuses)


@pytest.mark.parametrize(
    ("name", "text", "expected"),
    [
        ("Bad_Name.md", "# Valid title\n", "lowercase hyphenated"),
        ("missing-title.md", "No title\n", "level-one title"),
        (
            "possible-secret.md",
            "# Secret\n\napi_key = abcdefghijklmnopqrstuvwxyz\n",
            "possible secret",
        ),
        (
            "private-key.md",
            "# Key\n\n-----BEGIN PRIVATE KEY-----\n",
            "private-key marker",
        ),
    ],
)
def test_check_rejects_malformed_or_sensitive_memory(
    tmp_path, monkeypatch, name, text, expected
):
    repo = _repo(tmp_path)
    _write_memory(repo, name, text)
    monkeypatch.setattr("dotfiles.project_memory._is_git_ignored", lambda *args: True)

    statuses = check_project_memory(repo)

    assert any(not status.ok and expected in status.message for status in statuses)


def test_check_rejects_nested_directories_and_symlinks(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    memory_dir = initialize_project_memory(repo)
    (memory_dir / "nested").mkdir()
    target = tmp_path / "outside.md"
    target.write_text("# Outside\n", encoding="utf-8")
    (memory_dir / "linked.md").symlink_to(target)
    monkeypatch.setattr("dotfiles.project_memory._is_git_ignored", lambda *args: True)

    statuses = check_project_memory(repo)

    messages = {status.message for status in statuses if not status.ok}
    assert "nested directories are not allowed" in messages
    assert "symlinks are not allowed" in messages


def test_migration_deduplicates_mirrored_safe_memories(tmp_path):
    repo = _repo(tmp_path)
    text = "# Redis tests\n\nIntegration tests require Redis.\n"
    for relative in (Path(".claude/memory"), Path(".codex/memories")):
        directory = repo / relative
        directory.mkdir(parents=True)
        (directory / "2026-08-14-redis-tests.md").write_text(text, encoding="utf-8")

    actions = plan_legacy_migration(repo)

    assert [action.action for action in actions] == ["migrate", "duplicate"]
    assert actions[0].target == ".agents/memory/redis-tests.md"
    assert not (repo / ".agents" / "memory" / "redis-tests.md").exists()


def test_migration_apply_copies_but_retains_legacy_source(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    source = repo / ".claude" / "memory" / "redis-tests.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Redis tests\n\nIntegration tests require Redis.\n")
    monkeypatch.setattr("dotfiles.project_memory._is_git_ignored", lambda *args: True)

    actions = plan_legacy_migration(repo, apply=True)

    target = repo / ".agents" / "memory" / "redis-tests.md"
    assert actions[0].message == "copied"
    assert target.read_text() == source.read_text()
    assert source.is_file()


def test_migration_apply_refuses_unverified_ignore_rule(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    source = repo / ".claude" / "memory" / "redis-tests.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Redis tests\n\nIntegration tests require Redis.\n")
    monkeypatch.setattr("dotfiles.project_memory._is_git_ignored", lambda *args: False)

    actions = plan_legacy_migration(repo, apply=True)

    assert actions[0].action == "review"
    assert "ignore rule" in actions[0].message
    assert not (repo / ".agents" / "memory" / "redis-tests.md").exists()


def test_migration_requires_manual_review_for_session_summaries(tmp_path):
    repo = _repo(tmp_path)
    source = repo / ".agents" / "memories" / "handoff.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "# Handoff\n\n## Request\nDo work.\n\n## Validation\nTests passed.\n"
    )

    actions = plan_legacy_migration(repo, apply=True)

    assert actions[0].action == "review"
    assert "session summary" in actions[0].message
    assert not (repo / ".agents" / "memory" / "handoff.md").exists()


def test_migration_reports_target_conflict_without_overwriting(tmp_path):
    repo = _repo(tmp_path)
    source = repo / ".claude" / "memory" / "redis-tests.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Old\n\nOld content.\n")
    target = _write_memory(repo, "redis-tests.md", "# Current\n\nCurrent content.\n")

    actions = plan_legacy_migration(repo, apply=True)

    assert actions[0].action == "conflict"
    assert target.read_text() == "# Current\n\nCurrent content.\n"


def test_list_and_check_json_are_machine_readable(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    _write_memory(repo, "redis-tests.md", "# Redis tests\n")
    monkeypatch.setattr("dotfiles.project_memory._is_git_ignored", lambda *args: True)

    assert run_memory_list(repo, as_json=True) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed[0]["name"] == "redis-tests.md"

    assert run_memory_check(repo, as_json=True) == 0
    checked = json.loads(capsys.readouterr().out)
    assert all(item["level"] != "error" for item in checked)
