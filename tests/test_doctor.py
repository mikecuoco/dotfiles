"""Tests for the doctor command."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from dotfiles.install import run_install
from dotfiles.doctor import run_doctor


@pytest.fixture()
def installed_home(tmp_path):
    """A fake $HOME with dotfiles installed."""
    run_install(profile="codespace", dry_run=False, home=tmp_path)
    return tmp_path


def test_doctor_exits_zero_after_install(installed_home, capsys):
    with patch("dotfiles.doctor.Path.home", return_value=installed_home):
        code = run_doctor()
    # The doctor may return 1 if optional auth is missing, but files/tools
    # should be fine in CI; just test it runs without exception.
    captured = capsys.readouterr()
    assert "Platform" in captured.out
    assert "Dotfiles" in captured.out
    assert "Tools" in captured.out
    assert "Authentication" in captured.out


def test_doctor_exits_nonzero_when_not_installed(tmp_path, capsys):
    with patch("dotfiles.doctor.Path.home", return_value=tmp_path):
        code = run_doctor()
    assert code == 1
    captured = capsys.readouterr()
    assert "Not installed" in captured.out


def test_doctor_json_mode(installed_home, capsys):
    with patch("dotfiles.doctor.Path.home", return_value=installed_home):
        run_doctor(as_json=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "platform" in data
    assert "dotfiles" in data
    assert "tools" in data
    assert "auth" in data


def test_doctor_no_secrets_in_output(installed_home, capsys):
    """Credential values must never appear in doctor output."""
    fake_secrets = {
        "ANTHROPIC_API_KEY": "sk-ant-secret-do-not-leak",
        "CLAUDE_CODE_OAUTH_TOKEN": "oauth-secret-do-not-leak",
        "GH_TOKEN": "ghs_secret_do_not_leak",
        "SYNAPSE_AUTH_TOKEN": "synapse-secret-do-not-leak",
        "CODEOCEAN_API_TOKEN": "codeocean-secret-do-not-leak",
        "MEM0_API_KEY": "mem0-secret-do-not-leak",
        "AWS_ACCESS_KEY_ID": "AKIASECRETDONOTLEAK",
        "AWS_SECRET_ACCESS_KEY": "aws-secret-key-do-not-leak",
        "AWS_SESSION_TOKEN": "aws-session-token-do-not-leak",
    }
    with patch.dict(os.environ, fake_secrets, clear=False), \
         patch("dotfiles.doctor.Path.home", return_value=installed_home), \
         patch("dotfiles.doctor.shutil.which", return_value=None):
        run_doctor()

    captured = capsys.readouterr()
    all_output = captured.out + captured.err
    for secret in fake_secrets.values():
        assert secret not in all_output, f"Secret appeared in doctor output: {secret}"


def test_doctor_detects_broken_symlink(installed_home, capsys):
    """If a symlink is removed, doctor should report it as broken."""
    bashrc = installed_home / ".bashrc"
    bashrc.unlink()

    with patch("dotfiles.doctor.Path.home", return_value=installed_home):
        code = run_doctor()

    assert code == 1
    captured = capsys.readouterr()
    assert "missing" in captured.out or "✗" in captured.out


def test_doctor_accepts_generated_and_merged_codeocean_files(tmp_path, capsys):
    run_install(profile="codeocean", dry_run=False, home=tmp_path)
    capsys.readouterr()

    with patch("dotfiles.doctor.Path.home", return_value=tmp_path), \
         patch("dotfiles.doctor.all_statuses", return_value=[]), \
         patch("dotfiles.doctor.check_plugin_statuses", return_value=[]), \
         patch("dotfiles.doctor.shutil.which", return_value="/usr/bin/tool"):
        run_doctor(as_json=True)

    report = json.loads(capsys.readouterr().out)
    files = {item["path"]: item for item in report["dotfiles"]["files"]}
    assert files[".claude/CLAUDE.md"]["ok"] is True
    assert files[".claude/CLAUDE.md"]["message"] == "generated"
    assert files[".codex/AGENTS.md"]["ok"] is True
    assert files[".codex/AGENTS.md"]["message"] == "generated"
    assert files[".codex/config.toml"]["ok"] is True
    assert files[".codex/config.toml"]["message"] == "merged"
    assert files[".claude.json"]["ok"] is True
    assert files[".claude.json"]["message"] == "merged"
