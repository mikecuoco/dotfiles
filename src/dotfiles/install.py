"""Safe, idempotent dotfiles installer."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from ._toml import tomllib
from .agent_skills import run_bundled_skills_setup
from .profiles import (
    LinkSpec,
    compose_sources,
    group_links,
    load_profiles,
    resolve_links,
)
from .platform import detect_platform


# Location of the installer state file, relative to $HOME
_STATE_FILE = Path(".config/dotfiles/state.json")
# Location of the active profile name (read by .bash_profile at shell startup)
_PROFILE_FILE = Path(".config/dotfiles/profile")


class Result(Enum):
    UNCHANGED = auto()           # Already symlinked to the correct target
    LINKED = auto()              # New symlink created
    BACKED_UP_AND_LINKED = auto()  # Existing file backed up, then linked
    MERGED = auto()              # Defaults merged into a mutable config file
    DRY = auto()                 # Would have been linked (dry-run)
    ERROR = auto()


@dataclass
class _Report:
    result: Result
    dst: Path
    src: Path
    backup: Optional[Path] = None
    error: Optional[str] = None


def get_resources_dir() -> Path:
    """Return the path to the ``resources/`` directory bundled with this package.

    Works for both editable (``pip install -e .``) and installed
    (``uv tool install``) builds because it uses ``__file__`` rather than
    ``importlib.resources``.
    """
    return Path(__file__).parent / "resources"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_dst(dst_rel: str, home: Path, claude_home: Path) -> Path:
    """Return the absolute destination path for *dst_rel*.

    Paths that begin with ``.claude`` are rooted at *claude_home*; everything
    else is rooted at *home*.  When *claude_home* equals *home* (the common
    case) this is equivalent to ``home / dst_rel`` for all paths.
    """
    if Path(dst_rel).parts[0] == ".claude":
        return claude_home / dst_rel
    return home / dst_rel


# ── Public entry points ───────────────────────────────────────────────────────

def run_install(
    profile: Optional[str] = None,
    dry_run: bool = False,
    home: Optional[Path] = None,
    claude_home: Optional[Path] = None,
    quiet: bool = False,
) -> bool:
    """Install dotfiles for *profile*.

    Routine progress is verbose by default. If *quiet* is true, only errors are
    printed.

    *claude_home* overrides the base directory for ``.claude/`` destinations
    (config, skills).  On Code Ocean, this defaults to ``/root/capsule`` when
    that directory exists so that agent config lives inside the versioned
    capsule rather than in the ephemeral home directory.

    Returns ``True`` on success, ``False`` if any link failed.
    """
    home = home or Path.home()
    resources = get_resources_dir()

    # Detect / validate profile
    try:
        info = detect_platform(override=profile)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return False

    profile_name = info.platform

    # Resolve the base directory for .claude/* files.  On Code Ocean the
    # capsule lives at /root/capsule and is the only persistent location, so
    # we default claude_home there when it exists.
    if claude_home is None:
        if profile_name == "codeocean":
            _capsule = Path("/root/capsule")
            claude_home = _capsule if _capsule.is_dir() else home
        else:
            claude_home = home

    prefix = "[dry-run] " if dry_run else ""
    if not quiet:
        print(f"{prefix}Installing profile: {profile_name}")
        print(f"  Signals : {', '.join(info.signals)}")
        print(f"  Resources: {resources}")
        if claude_home != home:
            print(f"  Claude home: {claude_home}")
        print()

    # Resolve links for this profile
    profiles = load_profiles(resources)
    try:
        links = resolve_links(profile_name, profiles)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return False

    # Load previous state to know which files were previously generated
    existing_state = read_state(home)
    prev_generated: set[str] = set((existing_state or {}).get("generated", []))

    # Group links by mode. Appends compose with a base link; merge modes target
    # standalone mutable config files such as ~/.claude.json and Codex config.
    base_links, append_links, merges_by_dst = group_links(links)
    merge_links = list(merges_by_dst.values())

    # Install each link (concat when a dst has append entries)
    reports: list[_Report] = []
    generated_dsts: list[str] = []
    merged_dsts: list[str] = []
    for dst_rel, base in base_links.items():
        dst = _resolve_dst(dst_rel, home, claude_home)
        if dst_rel in append_links:
            srcs = [resources / base.src] + [resources / a.src for a in append_links[dst_rel]]
            rpt = _install_concat(
                srcs=srcs, dst=dst, dry_run=dry_run,
                previously_generated=(dst_rel in prev_generated),
            )
            if rpt.result != Result.ERROR:
                generated_dsts.append(dst_rel)
        else:
            rpt = _install_link(src=resources / base.src, dst=dst, dry_run=dry_run)
        reports.append(rpt)
        _print_line(rpt, quiet=quiet)

    for lnk in merge_links:
        merge_fn = _install_json_merge if lnk.mode == "merge-json" else _install_toml_merge
        rpt = merge_fn(src=resources / lnk.src, dst=_resolve_dst(lnk.dst, home, claude_home), dry_run=dry_run)
        if rpt.result != Result.ERROR:
            merged_dsts.append(lnk.dst)
        reports.append(rpt)
        _print_line(rpt, quiet=quiet)

    # First-party skills are local, portable resources and are part of the core
    # install. Downloaded GPTomics skill groups remain opt-in through
    # ``dotfiles skills install``.
    skill_statuses = []
    if not quiet:
        print("\nAgent skills")
    for label, target in (
        ("Claude Code", claude_home / ".claude" / "skills"),
        ("Codex", home / ".agents" / "skills"),
    ):
        if not quiet:
            print(f"  {label}")
        skill_statuses.extend(
            run_bundled_skills_setup(
                resources,
                target,
                dry_run=dry_run,
                quiet=quiet,
            )
        )

    # Persist state & profile name
    if not dry_run:
        _write_state(
            home,
            profile_name,
            resources,
            links,
            generated_dsts,
            merged_dsts,
        )
        _write_profile_file(home, profile_name)
        _configure_git_credential_helper(profile_name)

    # Summary
    n_linked = sum(
        1 for r in reports
        if r.result in (
            Result.LINKED,
            Result.BACKED_UP_AND_LINKED,
            Result.MERGED,
            Result.DRY,
        )
    )
    n_ok = sum(1 for r in reports if r.result == Result.UNCHANGED)
    n_err = sum(1 for r in reports if r.result == Result.ERROR)
    n_skill_err = sum(1 for status in skill_statuses if not status.installed)

    if not quiet:
        print()
        print(
            f"{'[dry-run] ' if dry_run else ''}Done: "
            f"{n_linked} installed, {n_ok} unchanged, "
            f"{n_err + n_skill_err} errors"
        )

    return n_err == 0 and n_skill_err == 0


def run_status(home: Optional[Path] = None) -> int:
    """Print the current installation state.  Returns exit code."""
    state = read_state(home)
    if not state:
        print("dotfiles not installed. Run: dotfiles install")
        return 1

    print(f"Profile:   {state['profile']}")
    print(f"Installed: {state['installed_at']}")
    print(f"Resources: {state['resources_dir']}")
    generated = set(state.get("generated", []))
    merged = set(state.get("merged", []))
    print(f"\nInstalled files ({len(state['links'])}):")
    for dst_rel, src_rel in sorted(state["links"].items()):
        dst = (home or Path.home()) / dst_rel
        if dst_rel in merged:
            sym = "+" if dst.is_file() and not dst.is_symlink() else "✗"
        elif dst_rel in generated:
            sym = "~" if dst.exists() else "✗"   # ~ = generated file
        else:
            sym = "✓" if dst.is_symlink() else "✗"
        print(f"  {sym} ~/{dst_rel}")
    return 0


def read_state(home: Optional[Path] = None) -> Optional[dict]:
    """Return the saved installer state dict, or None if not installed."""
    state_file = (home or Path.home()) / _STATE_FILE
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _backup_path(dst: Path) -> Path:
    """Return the timestamped sibling path used to preserve an existing file."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return dst.with_name(dst.name + f".dotfiles-backup.{ts}")


def _atomic_write(dst: Path, text: str, file_mode: int) -> None:
    """Replace *dst* with *text* via a same-directory temp file.

    Raises ``OSError`` on failure, after removing the temp file it created.
    """
    temporary: Optional[Path] = None
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=dst.parent,
            prefix=f".{dst.name}.",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.chmod(temporary, file_mode)
        os.replace(temporary, dst)
    except OSError:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        raise


def _install_link(src: Path, dst: Path, dry_run: bool) -> _Report:
    """Create symlink dst → src with backup-on-conflict semantics."""
    if not src.exists():
        return _Report(
            Result.ERROR, dst, src,
            error=f"Source not found: {src}",
        )

    # Already a valid symlink to our resource
    if dst.is_symlink():
        try:
            if dst.resolve() == src.resolve():
                return _Report(Result.UNCHANGED, dst, src)
        except OSError:
            pass  # broken symlink — treat as existing file

    backup: Optional[Path] = None

    if dst.exists() or dst.is_symlink():
        backup = _backup_path(dst)
        if not dry_run:
            dst.rename(backup)

    if dry_run:
        return _Report(Result.DRY, dst, src, backup=backup)

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.symlink_to(src)

    result = Result.BACKED_UP_AND_LINKED if backup else Result.LINKED
    return _Report(result, dst, src, backup=backup)


def _install_concat(
    srcs: list[Path],
    dst: Path,
    dry_run: bool,
    *,
    previously_generated: bool = False,
) -> _Report:
    """Write dst as the concatenation of multiple source files.

    Used when a profile appends to a parent's file (e.g. a profile-specific
    CLAUDE.md appended to the common one).  The result is a regular file, not
    a symlink, so it is re-generated on every install run.

    If *previously_generated* is True the existing dst was written by a prior
    install run and can be replaced without backup.  Otherwise (unmanaged user
    file) the existing content is backed up first.
    """
    for src in srcs:
        if not src.exists():
            return _Report(Result.ERROR, dst, srcs[0], error=f"Source not found: {src}")

    combined = compose_sources(srcs)

    # Idempotent: skip if dst already contains the same generated content
    if dst.exists() and not dst.is_symlink() and dst.read_text() == combined:
        return _Report(Result.UNCHANGED, dst, srcs[0])

    backup: Optional[Path] = None
    if dst.exists() or dst.is_symlink():
        if previously_generated:
            # Our own file — remove cleanly, no backup needed
            if not dry_run:
                dst.unlink()
        else:
            # Unmanaged user file — back it up
            backup = _backup_path(dst)
            if not dry_run:
                dst.rename(backup)

    if dry_run:
        return _Report(Result.DRY, dst, srcs[0], backup=backup)

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(combined)
    result = Result.BACKED_UP_AND_LINKED if backup else Result.LINKED
    return _Report(result, dst, srcs[0], backup=backup)


def _deep_merge_json(
    destination: dict,
    overlay: dict,
) -> dict:
    """Recursively apply *overlay* to *destination*, preserving other keys."""
    merged = dict(destination)
    for key, value in overlay.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_json(current, value)
        else:
            merged[key] = value
    return merged


def _install_json_merge(src: Path, dst: Path, dry_run: bool) -> _Report:
    """Atomically merge a JSON object into a mutable destination file."""
    if not src.is_file():
        return _Report(Result.ERROR, dst, src, error=f"Source not found: {src}")
    if dst.is_symlink():
        return _Report(
            Result.ERROR,
            dst,
            src,
            error="refusing to merge JSON through a symlink",
        )

    try:
        overlay = json.loads(src.read_text(encoding="utf-8"))
        if not isinstance(overlay, dict):
            raise ValueError("merge source must contain a JSON object")

        if dst.exists():
            existing = json.loads(dst.read_text(encoding="utf-8"))
            if not isinstance(existing, dict):
                raise ValueError("merge destination must contain a JSON object")
            file_mode = dst.stat().st_mode & 0o777
        else:
            existing = {}
            file_mode = 0o600

        merged = _deep_merge_json(existing, overlay)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        return _Report(Result.ERROR, dst, src, error=f"JSON merge failed: {exc}")

    if merged == existing:
        return _Report(Result.UNCHANGED, dst, src)
    if dry_run:
        return _Report(Result.DRY, dst, src)

    try:
        _atomic_write(dst, json.dumps(merged, indent=2) + "\n", file_mode)
    except OSError as exc:
        return _Report(Result.ERROR, dst, src, error=f"JSON merge failed: {exc}")

    return _Report(Result.MERGED, dst, src)


_TOML_BLOCK_START = "# >>> dotfiles managed Codex preferences >>>"
_TOML_BLOCK_END = "# <<< dotfiles managed Codex preferences <<<"


def _toml_conflicts(
    destination: dict,
    overlay: dict,
    prefix: tuple[str, ...] = (),
) -> list[str]:
    """Return leaf paths that an unmanaged TOML file already defines."""
    conflicts: list[str] = []
    for key, value in overlay.items():
        if key not in destination:
            continue
        current = destination[key]
        path = prefix + (key,)
        if isinstance(current, dict) and isinstance(value, dict):
            conflicts.extend(_toml_conflicts(current, value, path))
        else:
            conflicts.append(".".join(path))
    return conflicts


def _strip_managed_toml_block(text: str) -> tuple[str, bool]:
    """Remove the installer-owned block while preserving all other bytes."""
    starts = text.count(_TOML_BLOCK_START)
    ends = text.count(_TOML_BLOCK_END)
    if starts == 0 and ends == 0:
        return text, False
    if starts != 1 or ends != 1:
        raise ValueError("malformed managed preference markers")

    start = text.index(_TOML_BLOCK_START)
    end = text.index(_TOML_BLOCK_END, start) + len(_TOML_BLOCK_END)
    if end < len(text) and text[end] == "\n":
        end += 1
    if end < len(text) and text[end] == "\n":
        end += 1
    return text[:start] + text[end:], True


def _install_toml_merge(src: Path, dst: Path, dry_run: bool) -> _Report:
    """Atomically add or refresh a marker-owned TOML preference block.

    The source uses root-level dotted keys, so it can be prepended without
    changing the scope of tables already owned by the Codex app. Existing
    unmanaged keys are never overwritten: a collision is reported instead.
    """
    if not src.is_file():
        return _Report(Result.ERROR, dst, src, error=f"Source not found: {src}")
    if dst.is_symlink():
        return _Report(
            Result.ERROR,
            dst,
            src,
            error="refusing to merge TOML through a symlink",
        )

    try:
        overlay_text = src.read_text(encoding="utf-8").rstrip() + "\n"
        overlay = tomllib.loads(overlay_text)
        if dst.exists():
            existing_text = dst.read_text(encoding="utf-8")
            file_mode = dst.stat().st_mode & 0o777
        else:
            existing_text = ""
            file_mode = 0o600

        unmanaged_text, had_managed_block = _strip_managed_toml_block(existing_text)
        unmanaged = tomllib.loads(unmanaged_text) if unmanaged_text.strip() else {}
        conflicts = _toml_conflicts(unmanaged, overlay)
        if conflicts:
            joined = ", ".join(conflicts)
            raise ValueError(f"unmanaged destination already defines: {joined}")

        managed_block = (
            f"{_TOML_BLOCK_START}\n"
            f"{overlay_text}"
            f"{_TOML_BLOCK_END}\n\n"
        )
        merged_text = managed_block + unmanaged_text
        tomllib.loads(merged_text)
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        return _Report(Result.ERROR, dst, src, error=f"TOML merge failed: {exc}")

    if had_managed_block and merged_text == existing_text:
        return _Report(Result.UNCHANGED, dst, src)
    if dry_run:
        return _Report(Result.DRY, dst, src)

    try:
        _atomic_write(dst, merged_text, file_mode)
    except OSError as exc:
        return _Report(Result.ERROR, dst, src, error=f"TOML merge failed: {exc}")

    return _Report(Result.MERGED, dst, src)


def _print_line(rpt: _Report, *, quiet: bool = False) -> None:
    if quiet and rpt.result != Result.ERROR:
        return

    # Show the path relative to home (e.g. .claude/CLAUDE.md not just CLAUDE.md)
    home = Path.home()
    try:
        display = str(rpt.dst.relative_to(home))
    except ValueError:
        display = str(rpt.dst)

    if rpt.result == Result.UNCHANGED:
        print(f"  ✓ ~/{display}")
    elif rpt.result == Result.LINKED:
        print(f"  → ~/{display}")
    elif rpt.result == Result.BACKED_UP_AND_LINKED:
        print(f"  → ~/{display}  (backed up: {rpt.backup.name})")
    elif rpt.result == Result.MERGED:
        print(f"  + ~/{display}  (merged defaults)")
    elif rpt.result == Result.DRY:
        bak = f"  (would back up: {rpt.backup.name})" if rpt.backup else ""
        print(f"  [dry] → ~/{display}{bak}")
    else:
        print(f"  ✗ ~/{display}  ERROR: {rpt.error}", file=sys.stderr)


def _write_state(
    home: Path,
    profile_name: str,
    resources: Path,
    links: list[LinkSpec],
    generated_dsts: list[str],
    merged_dsts: list[str],
) -> None:
    state_file = home / _STATE_FILE
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "profile": profile_name,
        "resources_dir": str(resources),
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "links": {lnk.dst: lnk.src for lnk in links},
        "generated": generated_dsts,
        "merged": merged_dsts,
    }
    state_file.write_text(json.dumps(state, indent=2) + "\n")


def _write_profile_file(home: Path, profile_name: str) -> None:
    """Write the active profile name so ``.bash_profile`` can read it."""
    profile_file = home / _PROFILE_FILE
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    profile_file.write_text(profile_name + "\n")


def _configure_git_credential_helper(profile_name: str) -> None:
    """Configure git credential helper appropriate for the platform."""
    if not shutil.which("git"):
        return

    def _git_cfg(key: str, value: str) -> None:
        subprocess.run(
            ["git", "config", "--global", key, value],
            check=False, capture_output=True,
        )

    if profile_name == "macos":
        # On macOS, use gh credential helper via PATH (not hardcoded Homebrew path)
        _git_cfg(
            "credential.https://github.com.helper",
            "!/usr/bin/env gh auth git-credential",
        )
        _git_cfg(
            "credential.https://gist.github.com.helper",
            "!/usr/bin/env gh auth git-credential",
        )
    elif profile_name in ("codespace",):
        # Codespaces handles GitHub auth natively; gh is always available
        if shutil.which("gh"):
            _git_cfg(
                "credential.https://github.com.helper",
                "gh auth git-credential",
            )
    elif profile_name == "cluster":
        # On HPC clusters, use plaintext store (no keychain)
        _git_cfg("credential.helper", "store")
