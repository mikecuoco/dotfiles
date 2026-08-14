"""Update the installed dotfiles package and apply its latest resources."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence


_REPOSITORY_URL = "git+https://github.com/mikecuoco/dotfiles.git"


def run_update(
    profile: Optional[str] = None,
    dry_run: bool = False,
    quiet: bool = False,
) -> int:
    """Upgrade dotfiles, then install the freshly downloaded resources.

    The package can be installed either as a uv tool (the recommended path) or
    through pip.  Re-running the install in a new Python process is important:
    it ensures the resources come from the version that was just downloaded.
    """
    upgrade_cmd = _upgrade_command()
    install_cmd = [sys.executable, "-m", "dotfiles", "install"]
    if profile:
        install_cmd.extend(["--profile", profile])
    if quiet:
        install_cmd.append("--quiet")

    if dry_run:
        print("[dry-run] Would update dotfiles with:")
        print(f"  {_format_command(upgrade_cmd)}")
        print("[dry-run] Would apply the updated dotfiles with:")
        print(f"  {_format_command([*install_cmd, '--dry-run'])}")
        return 0

    print("Updating dotfiles package...")
    try:
        upgraded = subprocess.run(upgrade_cmd, check=False)
    except OSError as exc:
        print(f"Error: could not update dotfiles: {exc}", file=sys.stderr)
        return 1
    if upgraded.returncode:
        print("Error: dotfiles package update failed; nothing was applied.", file=sys.stderr)
        return upgraded.returncode

    print("Applying updated dotfiles...")
    try:
        installed = subprocess.run(install_cmd, check=False)
    except OSError as exc:
        print(f"Error: package updated but dotfiles could not be applied: {exc}", file=sys.stderr)
        return 1
    return installed.returncode


def _upgrade_command() -> list[str]:
    """Choose the updater that owns the current installation when detectable."""
    # Do not resolve this path: virtual-environment Python executables are
    # commonly symlinks to a system interpreter, which would hide the uv tool
    # directory we need to identify.
    executable = Path(sys.executable)
    if _is_uv_tool(executable) and shutil.which("uv"):
        return ["uv", "tool", "upgrade", "mike-dotfiles"]
    return [sys.executable, "-m", "pip", "install", "--upgrade", _REPOSITORY_URL]


def _is_uv_tool(executable: Path) -> bool:
    """Whether *executable* belongs to uv's isolated mike-dotfiles tool env."""
    return any(
        parent.name == "mike-dotfiles" and parent.parent.name == "tools"
        for parent in executable.parents
    )


def _format_command(command: Sequence[str]) -> str:
    """Render a command for display without relying on a shell."""
    return " ".join(command)
