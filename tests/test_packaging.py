"""Packaging compatibility checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent


def test_legacy_setup_py_reports_project_name():
    """Legacy setuptools installers can read the compatibility entry point."""
    pytest.importorskip("setuptools")

    result = subprocess.run(
        [sys.executable, "setup.py", "--name"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "mike-dotfiles"
