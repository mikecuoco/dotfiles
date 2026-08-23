"""Shared fixtures.

Dotfile installation is chezmoi's job, so tests that need an installed $HOME
drive the real binary against a throwaway destination rather than reimplementing
what apply does. Where chezmoi is unavailable those tests skip rather than fail.

Nothing here imports from the repository -- there is no Python package to
install. `pytest` works from a bare checkout; the only external requirement is
the chezmoi binary itself.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_TEMPLATE = REPO_ROOT / "home" / ".chezmoi.toml.tmpl"
SYNC_SCRIPT = REPO_ROOT / "home" / "dot_local" / "bin" / "executable_dotfiles-sync"

requires_chezmoi = pytest.mark.skipif(
    shutil.which("chezmoi") is None,
    reason="chezmoi is not installed",
)

#: Profiles that can be installed directly. `common` is a composition layer.
INSTALLABLE_PROFILES = ("macos", "linux", "cluster", "codeocean", "codespace")

#: Variables that move chezmoi's own config and state out of $HOME. Pinning HOME
#: is not enough on their own account: chezmoi honours $XDG_CONFIG_HOME over
#: $HOME, and GitHub's ubuntu runner images export it. Every test would then
#: share one config, so `promptStringOnce` would answer `profile` once for the
#: whole session and every later apply would silently install the first
#: profile -- `macos`, whatever the fixture asked for.
#:
#: Dropped rather than repointed, so each platform keeps the native default a
#: real machine would use (~/.config on Linux, Library/Application Support on
#: macOS) instead of a layout invented here.
_XDG_VARS = ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME")


def _env_without_xdg() -> dict:
    """A copy of the environment that leaves chezmoi anchored to $HOME."""
    env = {**os.environ}
    for var in _XDG_VARS:
        env.pop(var, None)
    return env


def _tmp_base_with_plain_permissions() -> Path | None:
    """A scratch base whose new directories get ordinary umask permissions.

    chezmoi records the mode it wrote for every directory and refuses to touch a
    target that changed underneath it. Where the system temporary directory
    carries an inherited default POSIX ACL -- GitHub Codespaces is one such
    environment -- a directory chezmoi creates as 0755 lands as 0754, so the very
    next apply reports `.agents has changed since chezmoi last wrote it` and
    blocks on a prompt that cannot be answered without a TTY.

    That is a property of the filesystem, not of these dotfiles: the same
    sequence is idempotent on any path with plain semantics. So probe the default
    location and, only if it mangles permissions, hand the fixtures somewhere
    that does not. Returns None when the default is already fine.
    """
    default = Path(tempfile.gettempdir())
    canary = default / f"chezmoi-perm-canary-{os.getpid()}"
    try:
        canary.mkdir(mode=0o755, exist_ok=True)
        plain = stat.S_IMODE(canary.stat().st_mode) == 0o755
    except OSError:
        plain = False
    finally:
        shutil.rmtree(canary, ignore_errors=True)
    if plain:
        return None
    fallback = Path.home() / ".cache" / "dotfiles-tests"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def pytest_configure(config):
    """Redirect pytest's scratch space when the default mangles permissions."""
    if config.option.basetemp:
        return
    base = _tmp_base_with_plain_permissions()
    if base is not None:
        config.option.basetemp = str(base / "pytest")


def chezmoi_env(home: Path, capsule: Path | None = None, scope: str = "") -> dict:
    """Environment pinning chezmoi to a throwaway destination.

    Every variable the templates read is pinned explicitly, never inherited. A
    developer with $DOTFILES_PROFILE exported would otherwise beat
    `init --promptString` (home/.chezmoi.toml.tmpl:24 reads the environment
    first), and an exported $DOTFILES_CHEZMOI_SCOPE would silently flip every
    render to mode = "file".

    $DOTFILES_CAPSULE_DIR defaults inside *home* rather than to the real
    /root/capsule: home/.chezmoiignore stats it for the codeocean profile, and
    `stat` raises -- aborting the whole apply -- when the path is unreadable
    rather than merely absent, which is the case for any non-root user.

    $DOTFILES_SKIP_PACKAGE_INSTALL keeps the suite hermetic. Every apply here
    gets a fresh $HOME and so an empty chezmoi state, which makes
    run_onchange_before_10-install-brew-packages.sh rerun for each one. It is a
    no-op on a developer machine that already has zoxide, uv, node, awscli and
    claude-code -- which is why this went unnoticed -- but on a machine missing
    any of them the suite would install it from the network once per apply.

    The $XDG_* variables are dropped (see _XDG_VARS) so the pinned $HOME is
    really where chezmoi keeps its config and persistent state.
    """
    env = _env_without_xdg()
    env.pop("DOTFILES_PROFILE", None)
    env["DOTFILES_CHEZMOI_SCOPE"] = scope
    env["DOTFILES_CAPSULE_DIR"] = str(capsule if capsule else home / "capsule")
    env["DOTFILES_SKIP_PACKAGE_INSTALL"] = "1"
    env["HOME"] = str(home)
    return env


def init_chezmoi(home: Path, profile: str, capsule: Path | None = None) -> None:
    """Point a throwaway $HOME at this repository and select *profile*."""
    subprocess.run(
        [
            "chezmoi", "init",
            "--source", str(REPO_ROOT),
            "--promptString", f"profile={profile}",
        ],
        env=chezmoi_env(home, capsule),
        capture_output=True,
        text=True,
        check=True,
    )


def apply_chezmoi(
    home: Path, profile: str, capsule: Path | None = None
) -> subprocess.CompletedProcess:
    """Install *profile* into *home*, returning the completed apply process."""
    init_chezmoi(home, profile, capsule)
    return subprocess.run(
        ["chezmoi", "apply"],
        env=chezmoi_env(home, capsule),
        capture_output=True,
        text=True,
        check=False,
    )


def chezmoi_status(home: Path, capsule: Path | None = None) -> str:
    """`chezmoi status` output for *home*; empty means nothing to do."""
    return subprocess.run(
        ["chezmoi", "status"],
        env=chezmoi_env(home, capsule),
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()


def _render_config(profile: str, scope: str = "") -> str:
    """Render home/.chezmoi.toml.tmpl for *profile*.

    `execute-template --init` treats stdin as a *config* template and does not
    load .chezmoitemplates, so it can only ever produce the config -- never a
    file that composes fragments. --init is a subcommand flag while --source is
    global, hence the argument order. $DOTFILES_PROFILE is what selects the
    profile, so promptStringOnce is never reached and this stays non-interactive.
    """
    env = {
        **_env_without_xdg(),
        "DOTFILES_PROFILE": profile,
        "DOTFILES_CHEZMOI_SCOPE": scope,
    }
    return subprocess.run(
        ["chezmoi", "--source", str(REPO_ROOT), "execute-template", "--init"],
        input=CONFIG_TEMPLATE.read_text(encoding="utf-8"),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@contextlib.contextmanager
def _config_file(profile: str, scope: str = ""):
    """The rendered config on disk, for passing to --config."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "chezmoi.toml"
        path.write_text(_render_config(profile, scope), encoding="utf-8")
        yield path


def render(template_relpath: str, profile: str) -> str:
    """Render a source template exactly as `chezmoi apply` would.

    Step two of the two-step render: the config from step one carries sourceDir
    (home/.chezmoi.toml.tmpl:49) and [data] profile, so .chezmoitemplates and
    .chezmoidata both load and `{{ template ... }}` resolves. That is the whole
    reason the config cannot simply be rendered inline.
    """
    body = (REPO_ROOT / "home" / template_relpath).read_text(encoding="utf-8")
    with _config_file(profile) as config:
        return subprocess.run(
            ["chezmoi", "--config", str(config), "execute-template"],
            input=body,
            env=_env_without_xdg(),
            capture_output=True,
            text=True,
            check=True,
        ).stdout


def sync_codeocean(
    home: Path, capsule: Path
) -> subprocess.CompletedProcess:
    """Run both Code Ocean passes via the managed dotfiles-sync script.

    Exercises the script itself rather than reimplementing its sequence, so the
    capsule tests are a real regression net for it.
    """
    init_chezmoi(home, "codeocean", capsule)
    return subprocess.run(
        ["sh", str(SYNC_SCRIPT)],
        env=chezmoi_env(home, capsule),
        capture_output=True,
        text=True,
        check=False,
    )
