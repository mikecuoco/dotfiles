"""The beaker-gpu-jobs contract: one shared CUDA+PyTorch base image with no
conda packages, and every project's env installed when the job starts."""
from __future__ import annotations

import re
import subprocess

from .conftest import REPO_ROOT

SKILL = REPO_ROOT / "home" / "dot_claude" / "skills" / "beaker-gpu-jobs"
DOCKERFILE = SKILL / "references" / "docker" / "Dockerfile"
PROJECT_ENV = SKILL / "references" / "docker" / "project-env"
SPEC = SKILL / "references" / "experiment-spec.yaml"


def _instructions():
    """Dockerfile instructions with comments and blank lines dropped."""
    return [line.strip() for line in DOCKERFILE.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def test_base_image_has_no_entrypoint():
    """Sessions need a plain shell and the batch command lives in the spec."""
    assert not any(line.upper().startswith("ENTRYPOINT") for line in _instructions())


def test_base_image_installs_no_conda_packages():
    """Project envs are installed at job start, never baked into the base."""
    runs = [line for line in _instructions() if line.upper().startswith("RUN")]
    assert not any(re.search(r"\b(conda|mamba|micromamba)\b", run) for run in runs), runs
    assert any(line.startswith("FROM pytorch/pytorch:") for line in _instructions())
    assert "COPY --chmod=755 project-env /usr/local/bin/project-env" in _instructions()


def test_project_env_script_parses():
    assert subprocess.run(["sh", "-n", str(PROJECT_ENV)], check=False).returncode == 0


def test_spec_installs_the_project_env_before_running():
    body = SPEC.read_text()
    assert body.index("project-env") < body.index("/code/<entry>.py")
