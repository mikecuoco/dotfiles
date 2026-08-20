"""Seam between the ``dotfiles`` CLI and the chezmoi binary.

chezmoi owns dotfile installation: what gets linked, generated or merged, and
where. This module is the only place that shells out to it, so the rest of the
package can ask questions ("which profile is active?", "is anything out of
date?") without knowing how chezmoi is invoked.

The source of truth for *what* is installed lives in ``home/`` at the root of
this repository — see ``home/.chezmoiignore`` and ``home/.chezmoidata/``.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

#: Environment variable read by ``home/.chezmoi.toml.tmpl`` to select a profile.
#: Also read by ``~/.bash_profile`` to pick the shell overlay, so the name means
#: the same thing on both sides.
PROFILE_ENV = "DOTFILES_PROFILE"

#: Selects the capsule pass in ``home/.chezmoiignore``. See ``apply()``.
SCOPE_ENV = "DOTFILES_CHEZMOI_SCOPE"

#: Overridable for testing; matches the gate in ``home/.chezmoiignore``.
CAPSULE_ENV = "DOTFILES_CAPSULE_DIR"
DEFAULT_CAPSULE = "/root/capsule"

BOOTSTRAP_HINT = (
    "chezmoi is installed but is not pointed at these dotfiles.\n"
    "Bootstrap it once with:\n"
    "  chezmoi init --apply --promptString profile=<profile> \\\n"
    "      https://github.com/mikecuoco/dotfiles.git\n"
    "or, from a local checkout:\n"
    "  chezmoi init --apply --source <path-to-checkout>"
)

INSTALL_HINT = (
    "chezmoi is not installed. Install it with:\n"
    '  sh -c "$(curl -fsLS get.chezmoi.io)" -- -b ~/.local/bin\n'
    "or, on macOS: brew install chezmoi"
)


class ChezmoiError(RuntimeError):
    """chezmoi is missing, or a chezmoi invocation failed."""


def capsule_dir() -> Path:
    """Directory holding versioned Code Ocean capsule state."""
    return Path(os.environ.get(CAPSULE_ENV, DEFAULT_CAPSULE))


def executable() -> str:
    """Absolute path to the chezmoi binary, or raise with an install hint."""
    found = shutil.which("chezmoi")
    if found is None:
        raise ChezmoiError(INSTALL_HINT)
    return found


def _run(
    args: list[str],
    env: Optional[dict] = None,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    """Invoke chezmoi. Output is captured unless the caller wants it streamed."""
    return subprocess.run(
        [executable(), *args],
        env={**os.environ, **(env or {})},
        capture_output=capture,
        text=True,
        check=False,
    )


# ── Queries ──────────────────────────────────────────────────────────────────

def data(env: Optional[dict] = None) -> dict:
    """Return ``chezmoi data`` as a dict, or ``{}`` when it cannot be read.

    An empty result means chezmoi has not been initialised yet, which callers
    treat as "not installed" rather than as an error.
    """
    result = _run(["data"], env=env)
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except ValueError:
        return {}


def active_profile() -> Optional[str]:
    """Profile chezmoi is currently configured with, or None if uninitialised."""
    return data().get("profile")


def source_dir() -> Optional[Path]:
    """The chezmoi source directory — this repository's ``home/``."""
    result = _run(["source-path"])
    if result.returncode != 0:
        return None
    path = result.stdout.strip()
    return Path(path) if path else None


def profiles() -> dict[str, str]:
    """Map profile name → description, read from ``home/.chezmoidata/``."""
    return data().get("descriptions", {})


def status() -> list[str]:
    """Lines from ``chezmoi status``; empty means everything matches."""
    result = _run(["status"])
    if result.returncode != 0:
        raise ChezmoiError(result.stderr.strip() or "chezmoi status failed")
    return [line for line in result.stdout.splitlines() if line.strip()]


def is_initialised() -> bool:
    return active_profile() is not None


def _require_source(env: Optional[dict] = None) -> None:
    """Fail loudly when chezmoi's source directory is not these dotfiles.

    Without this, `chezmoi init` on a fresh machine happily points at an empty
    ~/.local/share/chezmoi and `apply` becomes a silent no-op. ``layers`` comes
    from ``home/.chezmoidata/profiles.toml``, so its presence is the signal that
    the right source is configured.
    """
    if "layers" not in data(env=env):
        raise ChezmoiError(BOOTSTRAP_HINT)


def execute_template(
    template: Path,
    profile: Optional[str] = None,
    source: Optional[Path] = None,
) -> str:
    """Render *template* the way ``chezmoi apply`` would, for *profile*.

    Used to inspect generated content (the agent instruction files) without
    writing anything to disk.

    Rendering for an arbitrary profile takes two steps. ``--init`` treats its
    input as a *config* template and deliberately does not load
    ``.chezmoitemplates``, so it cannot render a file that composes fragments.
    Instead the config is rendered first -- that is what $DOTFILES_PROFILE
    selects -- and then passed via ``--config`` for the real render.
    """
    root = _working_tree(source or template.parent)
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "chezmoi.toml"
        config.write_text(_render_config(root, profile))
        return _template_output(
            ["--config", str(config)], template.read_text(encoding="utf-8")
        )


def _render_config(root: Path, profile: Optional[str]) -> str:
    """Render ``.chezmoi.toml.tmpl`` for *profile* without touching real state."""
    source = root / "home" if (root / ".chezmoiroot").is_file() else root
    env = {PROFILE_ENV: profile} if profile else {}
    return _template_output(
        ["--source", str(root), "--init"],
        (source / ".chezmoi.toml.tmpl").read_text(encoding="utf-8"),
        env=env,
    )


def _template_output(
    flags: list[str], stdin: str, env: Optional[dict] = None
) -> str:
    """Run ``chezmoi execute-template`` with *stdin* as the template body."""
    # execute-template reads its template on stdin, which _run cannot supply.
    parts = list(flags)
    init = "--init" in parts
    if init:
        parts.remove("--init")
    result = subprocess.run(
        [executable(), *parts, "execute-template", *(["--init"] if init else [])],
        env={**os.environ, **(env or {})},
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ChezmoiError(result.stderr.strip() or "chezmoi execute-template failed")
    return result.stdout


def _working_tree(path: Path) -> Path:
    """Walk up from *path* to the directory holding ``.chezmoiroot``."""
    for candidate in (path, *path.parents):
        if (candidate / ".chezmoiroot").is_file():
            return candidate
    return path


# ── Mutations ────────────────────────────────────────────────────────────────

def resolve_profile(requested: Optional[str] = None) -> str:
    """Decide which profile to install, most explicit choice first.

    1. ``--profile`` on the command line
    2. whatever chezmoi is already configured with
    3. platform auto-detection

    Step 2 matters: without it, auto-detection would silently overwrite a
    deliberate choice (``cluster`` on a machine that merely looks like generic
    Linux) on every subsequent run.
    """
    if requested:
        return requested
    configured = active_profile()
    if configured:
        return configured
    from .platform import detect_platform
    return detect_platform().platform


def apply(
    profile: Optional[str] = None,
    dry_run: bool = False,
    quiet: bool = False,
) -> int:
    """Apply the active profile. Returns a shell exit code.

    On Code Ocean this runs twice. chezmoi has no per-path destination and a
    symlink from ``~/.claude`` into the capsule does not survive an apply, so
    capsule-resident agent config is a second pass with its own ``--destination``
    (see ``home/.chezmoiignore``). Everywhere else the second pass never runs.
    """
    chosen = resolve_profile(profile)
    env = {PROFILE_ENV: chosen}

    # Re-render ~/.config/chezmoi/chezmoi.toml so $DOTFILES_PROFILE takes
    # effect. chezmoi's promptStringOnce caches its answer in the persistent
    # state, where neither `init --promptString` nor `init --force` can reach
    # it; the environment variable is the supported override.
    init = _run(["init"], env=env)
    if init.returncode != 0:
        raise ChezmoiError(init.stderr.strip() or "chezmoi init failed")
    _require_source(env)

    args = ["apply"]
    if dry_run:
        args += ["--dry-run", "--verbose"]

    if not quiet:
        print(f"Applying dotfiles (profile: {chosen})")
    rc = _run(args, env=env, capture=False).returncode
    if rc or chosen != "codeocean":
        return rc

    return _apply_capsule(args, env, quiet)


def _apply_capsule(args: list[str], env: dict, quiet: bool) -> int:
    """Second pass writing capsule-resident agent config. No-op off Code Ocean."""
    capsule = capsule_dir()
    if not capsule.is_dir():
        return 0
    if not quiet:
        print(f"Applying capsule-resident agent config → {capsule}")
    return _run(
        [*args, "--destination", str(capsule)],
        env={**env, SCOPE_ENV: "capsule"},
        capture=False,
    ).returncode


def update(quiet: bool = False) -> int:
    """Pull the source repository, then apply — ``chezmoi update`` plus capsule."""
    _require_source()
    chosen = resolve_profile()
    env = {PROFILE_ENV: chosen}
    if not quiet:
        print(f"Updating dotfiles source and applying (profile: {chosen})")
    rc = _run(["update"], env=env, capture=False).returncode
    if rc or chosen != "codeocean":
        return rc
    return _apply_capsule(["apply"], env, quiet)
