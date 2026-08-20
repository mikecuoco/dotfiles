"""Tests for the safe, idempotent installer."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from dotfiles.install import run_install, read_state, get_resources_dir
from dotfiles._toml import tomllib


@pytest.fixture()
def fake_home(tmp_path):
    """Return a temporary directory that acts as $HOME."""
    return tmp_path


def test_install_codespace_dry_run(fake_home, capsys):
    ok = run_install(profile="codespace", dry_run=True, home=fake_home)
    assert ok is True
    captured = capsys.readouterr()
    assert "[dry-run]" in captured.out
    # Dry-run must not create any files
    assert list(fake_home.rglob(".*")) == []


def test_install_is_verbose_by_default(fake_home, capsys):
    ok = run_install(profile="codespace", dry_run=True, home=fake_home)

    assert ok is True
    output = capsys.readouterr().out
    assert "Installing profile: codespace" in output
    assert "Done:" in output


def test_install_quiet_suppresses_routine_output(fake_home, capsys):
    ok = run_install(
        profile="codespace",
        dry_run=True,
        home=fake_home,
        quiet=True,
    )

    assert ok is True
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_install_quiet_still_reports_errors(fake_home, capsys):
    ok = run_install(
        profile="nonexistent_profile_xyz",
        dry_run=True,
        home=fake_home,
        quiet=True,
    )

    assert ok is False
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Unknown profile" in captured.err


def test_install_codespace_creates_symlinks(fake_home):
    ok = run_install(profile="codespace", dry_run=False, home=fake_home)
    assert ok is True

    # Core files should be symlinked
    for name in (".bashrc", ".bash_profile", ".gitconfig", ".aliases", ".inputrc"):
        link = fake_home / name
        assert link.is_symlink(), f"Expected symlink: {name}"
        assert link.exists(), f"Dangling symlink: {name}"


def test_install_is_idempotent(fake_home):
    """Running install twice should be a no-op the second time (no backups created)."""
    run_install(profile="codespace", dry_run=False, home=fake_home)
    run_install(profile="codespace", dry_run=False, home=fake_home)

    # No backup files should exist after idempotent re-install
    backups = list(fake_home.rglob("*.dotfiles-backup.*"))
    assert backups == [], f"Unexpected backups after idempotent install: {backups}"


def test_install_backs_up_existing_file(fake_home):
    """An unmanaged file at a target path should be backed up, not silently overwritten."""
    existing = fake_home / ".aliases"
    existing.write_text("# my custom aliases\n")

    ok = run_install(profile="codespace", dry_run=False, home=fake_home)
    assert ok is True

    # Original content is backed up
    backups = list(fake_home.glob(".aliases.dotfiles-backup.*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "# my custom aliases\n"

    # Target is now a symlink
    assert (fake_home / ".aliases").is_symlink()


def test_install_writes_state_file(fake_home):
    run_install(profile="codespace", dry_run=False, home=fake_home)
    state = read_state(fake_home)
    assert state is not None
    assert state["profile"] == "codespace"
    assert "links" in state
    assert ".bashrc" in state["links"]


def test_install_writes_profile_file(fake_home):
    run_install(profile="codespace", dry_run=False, home=fake_home)
    profile_file = fake_home / ".config" / "dotfiles" / "profile"
    assert profile_file.exists()
    assert profile_file.read_text().strip() == "codespace"


def test_install_invalid_profile(fake_home, capsys):
    ok = run_install(profile="nonexistent_profile_xyz", dry_run=False, home=fake_home)
    assert ok is False
    captured = capsys.readouterr()
    assert "Unknown profile" in captured.err or "Unknown profile" in captured.out


def test_agent_config_directories_created(fake_home):
    run_install(profile="codespace", dry_run=False, home=fake_home)
    for relative in (".claude/CLAUDE.md", ".codex/AGENTS.md"):
        instructions = fake_home / relative
        assert instructions.exists()
        assert not instructions.is_symlink()
        assert ".agents/memory/" in instructions.read_text()

    global_ignore = (fake_home / ".gitignore").read_text()
    assert ".agents/memory/" in global_ignore
    assert ".claude/memory/" not in global_ignore
    assert ".codex/memories/" not in global_ignore


def test_install_does_not_create_project_memory_in_home(fake_home):
    run_install(profile="codespace", dry_run=False, home=fake_home)

    assert not (fake_home / ".agents" / "memory").exists()


def test_first_party_skills_install_for_both_agents(fake_home):
    run_install(profile="codespace", dry_run=False, home=fake_home)

    for root in (fake_home / ".claude" / "skills", fake_home / ".agents" / "skills"):
        for name in (
            "code-ocean-capsule",
            "jupyter-workflow",
            "scientific-plotting",
        ):
            assert (root / name / "SKILL.md").is_file()


def test_dry_run_does_not_write_state(fake_home):
    run_install(profile="codespace", dry_run=True, home=fake_home)
    assert read_state(fake_home) is None


def test_resources_dir_exists():
    resources = get_resources_dir()
    assert resources.is_dir()
    assert (resources / "profiles.toml").exists()


def test_generated_file_not_backed_up_on_reinstall(fake_home):
    """Re-running install on a profile with append links must not create backups."""
    run_install(profile="codeocean", dry_run=False, home=fake_home)
    claude_md = fake_home / ".claude" / "CLAUDE.md"
    assert claude_md.exists() and not claude_md.is_symlink()

    # Second install — content unchanged → UNCHANGED, no backup
    run_install(profile="codeocean", dry_run=False, home=fake_home)
    backups = list((fake_home / ".claude").glob("CLAUDE.md.dotfiles-backup.*"))
    assert backups == [], f"Unexpected backup(s) after idempotent reinstall: {backups}"


def test_generated_file_updated_without_backup(fake_home, tmp_path):
    """If a source file changes, the generated file is replaced cleanly — no backup."""
    run_install(profile="codeocean", dry_run=False, home=fake_home)

    # Patch the shared Code Ocean source to simulate an upstream edit
    from dotfiles.install import get_resources_dir
    co_src = get_resources_dir() / "codeocean" / "agents" / "PREFERENCES.md"
    original = co_src.read_text()
    try:
        co_src.write_text(original + "\n\n<!-- test patch -->")
        run_install(profile="codeocean", dry_run=False, home=fake_home)
    finally:
        co_src.write_text(original)

    backups = list((fake_home / ".claude").glob("CLAUDE.md.dotfiles-backup.*"))
    assert backups == [], f"Backup created for a generated file update: {backups}"

    claude_md = fake_home / ".claude" / "CLAUDE.md"
    assert "<!-- test patch -->" in claude_md.read_text()
    codex_md = fake_home / ".codex" / "AGENTS.md"
    assert "<!-- test patch -->" in codex_md.read_text()


def test_codeocean_merges_onboarding_without_replacing_claude_state(fake_home):
    claude_json = fake_home / ".claude.json"
    original = {
        "hasCompletedOnboarding": False,
        "oauthAccount": {"accountUuid": "preserve-me"},
        "projects": {"/code": {"hasTrustDialogAccepted": True}},
    }
    claude_json.write_text(json.dumps(original, indent=2) + "\n")

    ok = run_install(profile="codeocean", dry_run=False, home=fake_home)

    assert ok is True
    merged = json.loads(claude_json.read_text())
    assert merged["hasCompletedOnboarding"] is True
    assert merged["oauthAccount"] == original["oauthAccount"]
    assert merged["projects"] == original["projects"]
    assert not claude_json.is_symlink()


def test_codeocean_creates_private_claude_global_file(fake_home):
    run_install(profile="codeocean", dry_run=False, home=fake_home)
    claude_json = fake_home / ".claude.json"

    assert json.loads(claude_json.read_text()) == {"hasCompletedOnboarding": True}
    assert claude_json.stat().st_mode & 0o777 == 0o600


def test_codeocean_json_merge_is_idempotent(fake_home):
    run_install(profile="codeocean", dry_run=False, home=fake_home)
    claude_json = fake_home / ".claude.json"
    first = claude_json.read_bytes()
    first_mtime = claude_json.stat().st_mtime_ns

    run_install(profile="codeocean", dry_run=False, home=fake_home)

    assert claude_json.read_bytes() == first
    assert claude_json.stat().st_mtime_ns == first_mtime
    assert not list(fake_home.glob(".claude.json.dotfiles-backup.*"))


def test_codeocean_json_merge_dry_run_writes_nothing(fake_home):
    ok = run_install(profile="codeocean", dry_run=True, home=fake_home)

    assert ok is True
    assert not (fake_home / ".claude.json").exists()


def test_codeocean_json_merge_refuses_invalid_existing_state(fake_home):
    claude_json = fake_home / ".claude.json"
    claude_json.write_text("not json\n")

    ok = run_install(profile="codeocean", dry_run=False, home=fake_home)

    assert ok is False
    assert claude_json.read_text() == "not json\n"


def test_codeocean_json_merge_refuses_symlink_destination(fake_home):
    target = fake_home / "elsewhere.json"
    target.write_text('{"untouched": true}\n')
    claude_json = fake_home / ".claude.json"
    claude_json.symlink_to(target)

    ok = run_install(profile="codeocean", dry_run=False, home=fake_home)

    assert ok is False
    assert json.loads(target.read_text()) == {"untouched": True}


def test_codex_toml_merge_preserves_app_managed_state(fake_home):
    config = fake_home / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    original = (
        'notify = ["/Applications/Codex Notifier", "turn-ended"]\n'
        'model = "gpt-5.6-sol"\n'
        '\n'
        '[plugins."browser@openai-bundled"]\n'
        'enabled = true\n'
        '\n'
        '[projects."/work/example"]\n'
        'trust_level = "trusted"\n'
    )
    config.write_text(original)

    ok = run_install(profile="linux", dry_run=False, home=fake_home)

    assert ok is True
    merged = tomllib.loads(config.read_text())
    assert merged["notify"] == ["/Applications/Codex Notifier", "turn-ended"]
    assert merged["model"] == "gpt-5.6-sol"
    assert merged["plugins"]["browser@openai-bundled"]["enabled"] is True
    assert merged["projects"]["/work/example"]["trust_level"] == "trusted"
    assert merged["default_permissions"] == "dotfiles"
    assert merged["permissions"]["dotfiles"]["extends"] == ":workspace"
    assert not config.is_symlink()


def test_codex_toml_merge_is_idempotent(fake_home):
    run_install(profile="linux", dry_run=False, home=fake_home)
    config = fake_home / ".codex" / "config.toml"
    first = config.read_bytes()
    first_mtime = config.stat().st_mtime_ns

    run_install(profile="linux", dry_run=False, home=fake_home)

    assert config.read_bytes() == first
    assert config.stat().st_mtime_ns == first_mtime
    assert config.read_text().count("dotfiles managed Codex preferences >>>") == 1


def test_codex_toml_merge_creates_private_file(fake_home):
    run_install(profile="linux", dry_run=False, home=fake_home)
    config = fake_home / ".codex" / "config.toml"

    assert tomllib.loads(config.read_text())["default_permissions"] == "dotfiles"
    assert config.stat().st_mode & 0o777 == 0o600


def test_codex_toml_merge_dry_run_writes_nothing(fake_home):
    ok = run_install(profile="linux", dry_run=True, home=fake_home)

    assert ok is True
    assert not (fake_home / ".codex" / "config.toml").exists()


def test_codex_toml_merge_refuses_invalid_existing_state(fake_home):
    config = fake_home / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text("not valid = [toml\n")

    ok = run_install(profile="linux", dry_run=False, home=fake_home)

    assert ok is False
    assert config.read_text() == "not valid = [toml\n"


def test_codex_toml_merge_refuses_unmanaged_key_collision(fake_home):
    config = fake_home / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text('default_permissions = ":read-only"\n')

    ok = run_install(profile="linux", dry_run=False, home=fake_home)

    assert ok is False
    assert config.read_text() == 'default_permissions = ":read-only"\n'


def test_codex_toml_merge_refuses_symlink_destination(fake_home):
    target = fake_home / "elsewhere.toml"
    target.write_text('model = "preserve-me"\n')
    config = fake_home / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.symlink_to(target)

    ok = run_install(profile="linux", dry_run=False, home=fake_home)

    assert ok is False
    assert tomllib.loads(target.read_text()) == {"model": "preserve-me"}


# ── claude_home redirection (Code Ocean capsule) ──────────────────────────────

def test_codeocean_claude_home_redirects_claude_files(fake_home, tmp_path):
    """When claude_home is set, .claude/* files land there, not in home."""
    capsule = tmp_path / "capsule"
    capsule.mkdir()

    ok = run_install(
        profile="codeocean",
        dry_run=False,
        home=fake_home,
        claude_home=capsule,
    )

    assert ok is True
    # .claude config and generated CLAUDE.md go into the capsule
    assert (capsule / ".claude" / "CLAUDE.md").exists()
    assert (capsule / ".claude" / "settings.json").is_symlink()
    # Skills also land in the capsule
    assert (capsule / ".claude" / "skills" / "code-ocean-capsule" / "SKILL.md").is_file()

    # Non-.claude files (shell, git, etc.) still go into home
    assert (fake_home / ".bashrc").is_symlink()
    # .claude dir must NOT exist in home when capsule is different
    assert not (fake_home / ".claude").exists()


def test_codeocean_claude_home_dry_run_writes_nothing(fake_home, tmp_path):
    """dry_run=True must not write any files even with an explicit claude_home."""
    capsule = tmp_path / "capsule"
    capsule.mkdir()

    ok = run_install(
        profile="codeocean",
        dry_run=True,
        home=fake_home,
        claude_home=capsule,
    )

    assert ok is True
    assert list(capsule.rglob("*")) == []
    assert list(fake_home.rglob(".*")) == []


def test_codeocean_claude_home_shown_in_verbose_output(fake_home, tmp_path, capsys):
    """Installer should report the non-default claude_home so it is visible."""
    capsule = tmp_path / "capsule"
    capsule.mkdir()

    run_install(
        profile="codeocean",
        dry_run=True,
        home=fake_home,
        claude_home=capsule,
    )

    out = capsys.readouterr().out
    assert str(capsule) in out
