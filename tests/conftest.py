"""Shared fixtures.

Dotfile installation is chezmoi's job, so tests that need an installed $HOME
drive the real binary against a throwaway destination rather than reimplementing
what apply does. Where chezmoi is unavailable those tests skip rather than fail:
the package is still importable and usable without it, it just cannot install.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

requires_chezmoi = pytest.mark.skipif(
    shutil.which("chezmoi") is None,
    reason="chezmoi is not installed",
)

#: Profiles that can be installed directly. `common` is a composition layer.
INSTALLABLE_PROFILES = ("macos", "linux", "cluster", "codeocean", "codespace")


def chezmoi_env(home: Path) -> dict:
    """Environment pinning chezmoi (and the CLI) to a throwaway destination."""
    return {**os.environ, "HOME": str(home)}


def init_chezmoi(home: Path, profile: str) -> None:
    """Point a throwaway $HOME at this repository and select *profile*."""
    subprocess.run(
        [
            "chezmoi", "init",
            "--source", str(REPO_ROOT),
            "--promptString", f"profile={profile}",
        ],
        env=chezmoi_env(home),
        capture_output=True,
        text=True,
        check=True,
    )


def apply_chezmoi(home: Path, profile: str) -> subprocess.CompletedProcess:
    """Install *profile* into *home*, returning the completed apply process."""
    init_chezmoi(home, profile)
    return subprocess.run(
        ["chezmoi", "apply"],
        env=chezmoi_env(home),
        capture_output=True,
        text=True,
        check=False,
    )


def chezmoi_status(home: Path) -> str:
    """`chezmoi status` output for *home*; empty means nothing to do."""
    return subprocess.run(
        ["chezmoi", "status"],
        env=chezmoi_env(home),
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()


def render(template_relpath: str, profile: str) -> str:
    """Render a source template exactly as `chezmoi apply` would.

    Delegates to the package wrapper so the tests exercise the same two-step
    config-then-template path that `dotfiles agent-stats` uses.
    """
    from dotfiles import chezmoi

    return chezmoi.execute_template(
        REPO_ROOT / "home" / template_relpath,
        profile=profile,
        source=REPO_ROOT,
    )


@pytest.fixture()
def installed_home(tmp_path):
    """A throwaway $HOME with the codespace profile applied."""
    if shutil.which("chezmoi") is None:
        pytest.skip("chezmoi is not installed")
    result = apply_chezmoi(tmp_path, "codespace")
    assert result.returncode == 0, result.stderr
    return tmp_path
