"""Tests for command-line argument wiring."""
from __future__ import annotations

import runpy
import sys

import pytest

from dotfiles import cli
from dotfiles import install
from dotfiles import project_memory


def test_package_module_invokes_cli(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "main", lambda: calls.append(True))

    runpy.run_module("dotfiles", run_name="__main__")

    assert calls == [True]


@pytest.mark.parametrize(
    ("extra_args", "expected_quiet"),
    [([], False), (["-q"], True), (["--quiet"], True)],
)
def test_install_quiet_flag(monkeypatch, extra_args, expected_quiet):
    received = {}

    def fake_run_install(**kwargs):
        received.update(kwargs)
        return True

    monkeypatch.setattr(install, "run_install", fake_run_install)
    monkeypatch.setattr(
        sys,
        "argv",
        ["dotfiles", "install", "--profile", "codespace", *extra_args],
    )

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 0
    assert received["quiet"] is expected_quiet


def test_update_forwards_options(monkeypatch):
    received = {}

    def fake_run_update(**kwargs):
        received.update(kwargs)
        return 0

    from dotfiles import update
    monkeypatch.setattr(update, "run_update", fake_run_update)
    monkeypatch.setattr(
        sys,
        "argv",
        ["dotfiles", "update", "--profile", "linux", "--dry-run", "--quiet"],
    )

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 0
    assert received == {"profile": "linux", "dry_run": True, "quiet": True}


@pytest.mark.parametrize(
    ("subcommand", "extra_args", "function_name", "expected_kwargs"),
    [
        ("init", [], "run_memory_init", {}),
        ("list", ["--json"], "run_memory_list", {"as_json": True}),
        ("check", ["--json"], "run_memory_check", {"as_json": True}),
        ("migrate", ["--apply"], "run_memory_migrate", {"apply": True}),
    ],
)
def test_memory_commands_forward_options(
    monkeypatch, tmp_path, subcommand, extra_args, function_name, expected_kwargs
):
    received = {}

    def fake_command(repo, **kwargs):
        received["repo"] = repo
        received.update(kwargs)
        return 0

    monkeypatch.setattr(project_memory, function_name, fake_command)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dotfiles",
            "memory",
            subcommand,
            "--repo",
            str(tmp_path),
            *extra_args,
        ],
    )

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 0
    assert received == {"repo": tmp_path, **expected_kwargs}
