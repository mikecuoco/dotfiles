"""Tests for the ls/ll/la alias tier and the eza installer that backs it.

`la` was a shell function that rebuilt `ls -l` output with awk, addressing
columns by field number. On an AD/SSSD-joined host the primary group is
`domain users` -- two whitespace-separated tokens -- so every field after the
group shifted by one and `la` printed the size where the month belonged. The
fix was to stop parsing `ls` and let eza lay out its own columns.

What is asserted here is therefore the invariant that replaced the function:
each branch of the tier in `home/dot_aliases` defines all three aliases, and the
eza branch asks for octal permissions. The aliases are read back out of a real
bash that sourced the file, with `PATH` pinned to a stub directory, so the test
exercises the branch selection rather than grepping for text -- and it does not
depend on whether eza happens to be installed on the machine running pytest.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from .conftest import REPO_ROOT

ALIASES = REPO_ROOT / "home" / "dot_aliases"
FUNCTIONS = REPO_ROOT / "home" / "dot_functions"
INSTALLER = REPO_ROOT / "home" / "run_onchange_before_10-install-brew-packages.sh.tmpl"

#: Real binaries the alias file consults while picking a branch. Symlinked into
#: the stub PATH so the GNU-ls fallback is reached deterministically, instead of
#: dropping to the BSD arm just because `ls` was missing from a bare PATH.
_PASSTHROUGH = ("ls", "grep")

#: The stub PATH replaces PATH outright, so bash has to be invoked by absolute
#: path -- resolving it from the stub PATH would fail before the shell starts.
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="bash is not installed")


def _stub_path(tmp_path: Path, *stubs: str) -> str:
    """A PATH containing only `_PASSTHROUGH` plus the named fake binaries."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name in _PASSTHROUGH:
        real = shutil.which(name)
        if real and not (bin_dir / name).exists():
            (bin_dir / name).symlink_to(real)
    for name in stubs:
        stub = bin_dir / name
        stub.write_text("#!/bin/sh\nexit 0\n")
        stub.chmod(0o755)
    return str(bin_dir)


def _aliases(tmp_path: Path, *stubs: str) -> dict[str, str]:
    """Alias definitions bash ends up with after sourcing `home/dot_aliases`."""
    proc = subprocess.run(
        [BASH, "-c", f"source {ALIASES!s} >/dev/null 2>&1; alias"],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PATH": _stub_path(tmp_path, *stubs)},
    )
    found = {}
    for line in proc.stdout.splitlines():
        name, _, value = line.removeprefix("alias ").partition("=")
        found[name] = value.strip("'")
    return found


@pytest.mark.parametrize("stub", ["eza", "exa", None])
def test_every_branch_defines_the_full_ls_tier(tmp_path, stub):
    """`la` existed only in dot_functions before, so it is the regression."""
    defined = _aliases(tmp_path, *([stub] if stub else []))
    for name in ("ls", "ll", "la", "lsd"):
        assert name in defined, f"{name} undefined with stub={stub!r}"


def test_eza_branch_is_selected_and_asks_for_octal_permissions(tmp_path):
    defined = _aliases(tmp_path, "eza")
    assert defined["la"].startswith("eza ")
    # -o/--octal-permissions replacing the symbolic string is the whole point of
    # `la`; without --no-permissions eza prints both columns.
    assert "-o" in defined["la"].split()
    assert "--no-permissions" in defined["la"].split()
    # `ll` keeps the symbolic string, so the two aliases stay distinguishable.
    assert "--no-permissions" not in defined["ll"]


def test_fallback_branch_needs_no_eza(tmp_path):
    defined = _aliases(tmp_path)
    assert "eza" not in defined["la"]
    assert "exa" not in defined["la"]


def test_la_is_no_longer_a_shell_function():
    """The awk field-number parse must not come back alongside the alias."""
    assert "la()" not in FUNCTIONS.read_text()


def test_installer_installs_eza():
    body = INSTALLER.read_text()
    assert "install_eza()" in body, "helper missing"
    # Defining it without calling it is the easy way to get this wrong.
    assert any(
        line.strip() == "install_eza" for line in body.splitlines()
    ), "install_eza defined but never invoked"
    # musl on x86_64 survives the old glibc on cluster login nodes; aarch64
    # has no musl asset published.
    assert "eza_${_target}.tar.gz" in body
    assert "x86_64-unknown-linux-musl" in body
    assert "aarch64-unknown-linux-gnu" in body
