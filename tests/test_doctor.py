"""Tests for the doctor command.

File health now comes from `chezmoi status` rather than a manifest the
installer wrote, so these tests drive the real binary against a throwaway
$HOME. HOME is set in the environment rather than patching ``Path.home``:
chezmoi runs as a subprocess and only the environment reaches it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from dotfiles.doctor import run_doctor

from .conftest import apply_chezmoi, requires_chezmoi

pytestmark = requires_chezmoi


@pytest.fixture(autouse=True)
def isolate_plugin_checks(monkeypatch):
    """Doctor unit tests must not call a live Claude CLI or plugin registry."""
    monkeypatch.setattr("dotfiles.doctor.check_plugin_statuses", lambda resources: [])


@pytest.fixture()
def codeocean_home(tmp_path, monkeypatch):
    result = apply_chezmoi(tmp_path, "codeocean")
    assert result.returncode == 0, result.stderr
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def _minimal_env(home: Path) -> dict:
    """Just enough environment to run chezmoi, with no platform signals set."""
    return {"HOME": str(home), "PATH": os.environ["PATH"]}


def test_doctor_reports_all_sections(installed_home, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(installed_home))
    run_doctor()
    captured = capsys.readouterr()
    for section in ("Platform", "Dotfiles", "Tools", "Authentication"):
        assert section in captured.out


def test_doctor_exits_nonzero_when_not_installed(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    code = run_doctor()
    assert code == 1
    assert "Not installed" in capsys.readouterr().out


def test_doctor_json_mode(installed_home, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(installed_home))
    run_doctor(as_json=True)
    data = json.loads(capsys.readouterr().out)
    for key in ("platform", "dotfiles", "tools", "auth", "project_memory"):
        assert key in data


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
    env = {**fake_secrets, "HOME": str(installed_home)}
    with patch.dict(os.environ, env, clear=False), \
         patch("dotfiles.doctor._which", return_value=None):
        run_doctor()

    captured = capsys.readouterr()
    all_output = captured.out + captured.err
    for secret in fake_secrets.values():
        assert secret not in all_output, f"Secret appeared in doctor output: {secret}"


def test_clean_install_reports_no_discrepancies(codeocean_home, capsys):
    """A freshly applied profile has nothing out of date."""
    with patch("dotfiles.doctor.all_statuses", return_value=[]), \
         patch("dotfiles.doctor._which", return_value="/usr/bin/tool"):
        code = run_doctor(as_json=True)

    report = json.loads(capsys.readouterr().out)
    assert report["dotfiles"]["files"] == []
    assert report["dotfiles"]["profile"] == "codeocean"
    assert code == 0


def test_doctor_detects_removed_symlink(installed_home, monkeypatch, capsys):
    """Deleting a managed file shows up as something apply would restore."""
    monkeypatch.setenv("HOME", str(installed_home))
    (installed_home / ".bashrc").unlink()

    with patch("dotfiles.doctor.all_statuses", return_value=[]), \
         patch("dotfiles.doctor._which", return_value="/usr/bin/tool"):
        code = run_doctor(as_json=True)

    report = json.loads(capsys.readouterr().out)
    paths = {item["path"] for item in report["dotfiles"]["files"]}
    assert code == 1
    assert ".bashrc" in paths


def test_doctor_detects_modified_generated_instructions(
    installed_home, monkeypatch, capsys
):
    """Hand-editing a generated file is reported, not silently accepted."""
    monkeypatch.setenv("HOME", str(installed_home))
    (installed_home / ".codex" / "AGENTS.md").write_text("stale\n")

    with patch("dotfiles.doctor.all_statuses", return_value=[]), \
         patch("dotfiles.doctor._which", return_value="/usr/bin/tool"):
        code = run_doctor(as_json=True)

    report = json.loads(capsys.readouterr().out)
    entries = {item["path"]: item for item in report["dotfiles"]["files"]}
    assert code == 1
    assert ".codex/AGENTS.md" in entries
    assert entries[".codex/AGENTS.md"]["ok"] is False


def test_doctor_recognizes_documented_codeocean_runtime_signal(
    codeocean_home, capsys
):
    env = {**_minimal_env(codeocean_home), "CO_CAPSULE_ID": "capsule-id"}
    with patch.dict(os.environ, env, clear=True), \
         patch("dotfiles.doctor.all_statuses", return_value=[]), \
         patch("dotfiles.doctor.check_plugin_statuses", return_value=[]), \
         patch("dotfiles.doctor._which", return_value="/usr/bin/tool"):
        code = run_doctor(as_json=True)

    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["platform"]["name"] == "codeocean"
    assert report["platform"]["signals"] == ["CO_CAPSULE_ID set"]


def test_doctor_uses_installed_codeocean_profile_without_runtime_signal(
    codeocean_home, capsys
):
    """With no runtime signal, the chezmoi-configured profile is the evidence."""
    with patch.dict(os.environ, _minimal_env(codeocean_home), clear=True), \
         patch("dotfiles.doctor.all_statuses", return_value=[]), \
         patch("dotfiles.doctor.check_plugin_statuses", return_value=[]), \
         patch("dotfiles.doctor._which", return_value="/usr/bin/tool"), \
         patch("dotfiles.platform.platform.system", return_value="Linux"), \
         patch("dotfiles.platform.socket.gethostname", return_value="afff5427898f"):
        code = run_doctor(as_json=True)

    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["platform"] == {
        "name": "codeocean",
        "os": "Linux",
        "hostname": "afff5427898f",
        "signals": ["installed profile=codeocean"],
    }


def test_doctor_fails_for_unignored_project_memory(
    installed_home, tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("HOME", str(installed_home))
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".agents" / "memory").mkdir(parents=True)
    monkeypatch.setattr("dotfiles.project_memory._is_git_ignored", lambda *args: False)

    with patch("dotfiles.doctor.Path.cwd", return_value=repo), \
         patch("dotfiles.doctor.all_statuses", return_value=[]), \
         patch("dotfiles.doctor._which", return_value="/usr/bin/tool"):
        code = run_doctor(as_json=True)

    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert any(
        check["message"] == "not ignored by Git"
        for check in report["project_memory"]["checks"]
    )
