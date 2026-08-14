"""Tests for the top-level dotfiles update command."""
from __future__ import annotations

from pathlib import Path

from dotfiles import update


def test_update_dry_run_shows_both_steps(monkeypatch, capsys):
    monkeypatch.setattr(update, "_upgrade_command", lambda: ["uv", "tool", "upgrade", "mike-dotfiles"])

    assert update.run_update(profile="linux", dry_run=True, quiet=True) == 0

    output = capsys.readouterr().out
    assert "uv tool upgrade mike-dotfiles" in output
    assert "-m dotfiles install --profile linux --quiet --dry-run" in output


def test_update_stops_when_upgrade_fails(monkeypatch, capsys):
    calls = []

    class Result:
        returncode = 4

    def fake_run(command, check):
        calls.append(command)
        return Result()

    monkeypatch.setattr(update, "_upgrade_command", lambda: ["update-command"])
    monkeypatch.setattr(update.subprocess, "run", fake_run)

    assert update.run_update() == 4
    assert calls == [["update-command"]]
    assert "nothing was applied" in capsys.readouterr().err


def test_update_runs_fresh_install_after_upgrade(monkeypatch):
    calls = []

    class Result:
        returncode = 0

    def fake_run(command, check):
        calls.append(command)
        return Result()

    monkeypatch.setattr(update, "_upgrade_command", lambda: ["update-command"])
    monkeypatch.setattr(update.subprocess, "run", fake_run)

    assert update.run_update(profile="codespace", quiet=True) == 0
    assert calls == [
        ["update-command"],
        [update.sys.executable, "-m", "dotfiles", "install", "--profile", "codespace", "--quiet"],
    ]


def test_uv_tool_detection():
    assert update._is_uv_tool(Path("/Users/example/.local/share/uv/tools/mike-dotfiles/bin/python"))
    assert update._is_uv_tool(
        Path("/scratch/.dotfiles/envs/uv-tools/mike-dotfiles/bin/python")
    )
    assert not update._is_uv_tool(Path("/usr/bin/python3"))


def test_uv_tool_detection_uses_configured_directory(monkeypatch):
    monkeypatch.setenv("UV_TOOL_DIR", "/custom/tool-environments")
    executable = Path("/custom/tool-environments/mike-dotfiles/bin/python")
    assert update._is_uv_tool(executable)


def test_uv_tool_detection_uses_receipt_in_arbitrary_directory(tmp_path):
    root = tmp_path / "arbitrary" / "mike-dotfiles"
    root.mkdir(parents=True)
    (root / "uv-receipt.toml").write_text("")
    assert update._is_uv_tool(root / "bin" / "python")


def test_upgrade_finds_uv_outside_path(monkeypatch, tmp_path):
    uv = tmp_path / ".local" / "bin" / "uv"
    uv.parent.mkdir(parents=True)
    uv.write_text("")
    monkeypatch.setattr(update.sys, "executable", "/scratch/envs/uv-tools/mike-dotfiles/bin/python")
    monkeypatch.setattr(update.shutil, "which", lambda name: None)
    monkeypatch.setattr(update.Path, "home", lambda: tmp_path)

    assert update._upgrade_command() == [
        str(uv), "tool", "upgrade", "mike-dotfiles"
    ]


def test_uv_install_without_uv_does_not_fall_back_to_pip(monkeypatch, capsys):
    monkeypatch.setattr(update, "_find_uv", lambda: None)
    monkeypatch.setattr(
        update.sys,
        "executable",
        "/scratch/.dotfiles/envs/uv-tools/mike-dotfiles/bin/python",
    )

    assert update.run_update() == 1
    assert "uv-managed installation" in capsys.readouterr().err
