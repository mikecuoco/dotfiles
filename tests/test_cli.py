"""Tests for command-line argument wiring."""
from __future__ import annotations

import sys

import pytest

from dotfiles import cli
from dotfiles import install


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
