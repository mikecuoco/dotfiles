"""The agents-memory-check contract documented in docs/project-memory.md."""
from __future__ import annotations

import os
import subprocess

from .conftest import REPO_ROOT

CHECK = REPO_ROOT / "home" / "dot_local" / "bin" / "executable_agents-memory-check"

#: The developer's global gitignore (this repo's own dot_gitignore, once
#: installed) already ignores .agents/memory/, which would hide the
#: not-ignored case. Run git with no global or system config.
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def _repo(tmp_path, ignored=True):
    subprocess.run(["git", "init", "-q", str(tmp_path)], env=GIT_ENV, check=True)
    if ignored:
        (tmp_path / ".gitignore").write_text(".agents/memory/\n")
    memory = tmp_path / ".agents" / "memory"
    memory.mkdir(parents=True)
    return memory


def _check(repo):
    return subprocess.run(
        ["sh", str(CHECK), str(repo)],
        env=GIT_ENV, capture_output=True, text=True, check=False,
    )


def test_absent_memory_directory_is_not_an_error(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], env=GIT_ENV, check=True)
    assert _check(tmp_path).returncode == 0


def test_valid_memory_passes(tmp_path):
    memory = _repo(tmp_path)
    (memory / "build-uses-uv.md").write_text("# Build uses uv\n\nRun tests with uv.\n")
    result = _check(tmp_path)
    assert result.returncode == 0, result.stderr


def test_every_violation_is_reported(tmp_path):
    memory = _repo(tmp_path, ignored=False)
    (memory / "Bad_Name.md").write_text("# Title\n")
    (memory / "no-title.md").write_text("just text\n")
    (memory / "leaky.md").write_text("# Leak\n\napi_key = abcdefghijklmnop1234\n")

    result = _check(tmp_path)

    assert result.returncode == 1
    for expected in ("not ignored by Git", "Bad_Name.md", "no-title.md", "leaky.md"):
        assert expected in result.stderr, expected
