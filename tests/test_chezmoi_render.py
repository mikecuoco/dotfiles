"""End-to-end checks that chezmoi installs each profile correctly.

This replaces the parity harness that compared chezmoi against the Python
installer. With the installer gone there is nothing to diff against, so the
properties it verified are asserted directly: the right targets exist, they are
the right *kind* of thing (symlink vs generated vs merged), app-managed state
survives, and re-applying changes nothing.
"""
from __future__ import annotations

import json

import pytest

from dotfiles._toml import tomllib
from .conftest import (
    INSTALLABLE_PROFILES,
    apply_chezmoi,
    chezmoi_status,
    requires_chezmoi,
)

pytestmark = requires_chezmoi


#: Present for every profile, and symlinked back into the source tree.
COMMON_SYMLINKS = (
    ".bashrc",
    ".bash_profile",
    ".aliases",
    ".exports",
    ".functions",
    ".inputrc",
    ".gitconfig",
    ".gitignore",
    ".gitattributes",
    ".vimrc",
    ".condarc",
    ".dircolors",
    ".gemrc",
    ".aws/config",
    ".claude/settings.json",
)

#: Composed from fragments, so regular files rather than symlinks.
GENERATED = (".claude/CLAUDE.md", ".codex/AGENTS.md", ".config/dotfiles/profile")

#: Merged into whatever the app already wrote there.
MERGED = (".codex/config.toml",)

#: Overlay files that must appear for their profile and no other.
PROFILE_ONLY = {
    "macos": (".exports.macos", ".aliases.macos", ".functions.macos"),
    "linux": (".exports.linux",),
    "cluster": (".exports.cluster", ".functions.cluster", ".Rprofile"),
    "codeocean": (".exports.codeocean", ".claude.json"),
    "codespace": (".exports.codespace",),
}


@pytest.fixture(scope="module", params=INSTALLABLE_PROFILES)
def applied(request, tmp_path_factory):
    """Each profile applied once into its own throwaway $HOME."""
    home = tmp_path_factory.mktemp(request.param)
    result = apply_chezmoi(home, request.param)
    assert result.returncode == 0, result.stderr
    return request.param, home


def test_common_files_are_symlinks_into_the_source(applied):
    _, home = applied
    for rel in COMMON_SYMLINKS:
        target = home / rel
        assert target.is_symlink(), f"{rel} should be a symlink"
        assert target.resolve().is_file(), f"{rel} dangles"


def test_generated_files_are_regular_files(applied):
    """Composed and merged targets must not be symlinks into the repo.

    Symlinking them would mean an app writing to ~/.codex/config.toml would
    write straight into the git checkout -- the failure mode that had
    `git config --global` mutating the tracked .gitconfig.
    """
    profile, home = applied
    for rel in GENERATED + MERGED:
        target = home / rel
        assert target.is_file(), f"{rel} missing for {profile}"
        assert not target.is_symlink(), f"{rel} should be generated, not linked"


def test_profile_marker_matches_the_installed_profile(applied):
    """~/.bash_profile reads this file to pick the .exports.<profile> overlay."""
    profile, home = applied
    assert (home / ".config" / "dotfiles" / "profile").read_text() == f"{profile}\n"


def test_profile_overlays_are_exclusive(applied):
    """A profile gets its own overlays and nobody else's."""
    profile, home = applied
    for rel in PROFILE_ONLY[profile]:
        assert (home / rel).exists(), f"{profile} is missing {rel}"

    inherited = {"linux"} if profile in {"cluster", "codeocean", "codespace"} else set()
    for other, files in PROFILE_ONLY.items():
        if other == profile or other in inherited:
            continue
        for rel in files:
            assert not (home / rel).exists(), f"{profile} should not have {rel}"


def test_matplotlib_stylelib_installed_for_every_platform(applied):
    """One stylelib serves both platforms; macOS reaches it via MPLCONFIGDIR."""
    _, home = applied
    styles = home / ".config" / "matplotlib" / "stylelib"
    assert styles.is_dir()
    assert {p.name for p in styles.glob("*.mplstyle")} == {
        "cuoco-base.mplstyle",
        "cuoco-manuscript.mplstyle",
        "cuoco-presentation.mplstyle",
        "cuoco-poster.mplstyle",
    }


def test_vim_tree_is_per_file_symlinks(applied):
    """~/.vim expands to a real directory so vim's runtime state stays local."""
    _, home = applied
    vim = home / ".vim"
    assert vim.is_dir() and not vim.is_symlink()
    assert (vim / "colors" / "molokai.vim").is_symlink()


def test_apply_is_idempotent(applied):
    """A second apply must be a no-op."""
    profile, home = applied
    assert apply_chezmoi(home, profile).returncode == 0
    assert chezmoi_status(home) == ""


# ── merge semantics ──────────────────────────────────────────────────────────

APP_CONFIG = """\
# Written by Codex itself -- do not lose this comment.
model = "gpt-5"

[history]
persistence = "save-all"
"""


def test_codex_config_merge_preserves_app_managed_content(tmp_path):
    """The riskiest merge: comments, key order and tables must all survive."""
    (tmp_path / ".codex").mkdir()
    config = tmp_path / ".codex" / "config.toml"
    config.write_text(APP_CONFIG)

    assert apply_chezmoi(tmp_path, "linux").returncode == 0

    merged = config.read_text()
    assert "do not lose this comment" in merged
    assert 'model = "gpt-5"' in merged
    assert "[history]" in merged
    assert merged.count("# >>> dotfiles managed Codex preferences >>>") == 1
    parsed = tomllib.loads(merged)
    assert parsed["model"] == "gpt-5"
    assert parsed["history"]["persistence"] == "save-all"


def test_codex_config_merge_does_not_accrete_on_reapply(tmp_path):
    (tmp_path / ".codex").mkdir()
    config = tmp_path / ".codex" / "config.toml"
    config.write_text(APP_CONFIG)

    assert apply_chezmoi(tmp_path, "linux").returncode == 0
    first = config.read_text()
    assert apply_chezmoi(tmp_path, "linux").returncode == 0

    assert config.read_text() == first
    assert first.count("# >>> dotfiles managed Codex preferences >>>") == 1


def test_claude_json_merge_preserves_unrelated_keys(tmp_path):
    (tmp_path / ".claude.json").write_text(json.dumps({"userID": "abc123"}))
    assert apply_chezmoi(tmp_path, "codeocean").returncode == 0
    assert json.loads((tmp_path / ".claude.json").read_text()) == {
        "userID": "abc123",
        "hasCompletedOnboarding": True,
    }


def test_claude_json_is_private(tmp_path):
    """It can hold session state, so it must not be world-readable."""
    assert apply_chezmoi(tmp_path, "codeocean").returncode == 0
    mode = (tmp_path / ".claude.json").stat().st_mode & 0o777
    assert mode == 0o600, oct(mode)


# ── backup safety net ────────────────────────────────────────────────────────

def test_unmanaged_files_are_backed_up_before_first_apply(tmp_path):
    (tmp_path / ".bashrc").write_text("my own bashrc\n")
    assert apply_chezmoi(tmp_path, "linux").returncode == 0

    backups = list(tmp_path.glob(".bashrc.dotfiles-backup.*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "my own bashrc\n"
    assert (tmp_path / ".bashrc").is_symlink()


def test_backup_does_not_copy_whole_directories(tmp_path):
    """~/.config can be enormous; only leaf targets are ever preserved."""
    unrelated = tmp_path / ".config" / "some-other-app"
    unrelated.mkdir(parents=True)
    (unrelated / "state.bin").write_bytes(b"x" * 4096)

    assert apply_chezmoi(tmp_path, "linux").returncode == 0

    assert not list(tmp_path.glob(".config.dotfiles-backup.*"))
    assert (unrelated / "state.bin").read_bytes() == b"x" * 4096
