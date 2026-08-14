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
    assert not update._is_uv_tool(Path("/usr/bin/python3"))
