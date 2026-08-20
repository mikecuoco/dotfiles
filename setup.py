"""Compatibility entry point for legacy pip editable installs.

Modern installers use ``pyproject.toml`` and Hatchling. Some older images
still invoke ``setup.py develop`` for ``pip install -e``; keep this metadata
in sync with ``pyproject.toml`` so that path remains usable when setuptools is
available in the target interpreter.
"""

from pathlib import Path
from typing import List

from setuptools import find_packages, setup


PACKAGE_ROOT = Path(__file__).parent / "src" / "dotfiles"


def resource_files() -> List[str]:
    """Return bundled resource paths relative to the dotfiles package."""
    resources = PACKAGE_ROOT / "resources"
    return [str(path.relative_to(PACKAGE_ROOT)) for path in resources.rglob("*") if path.is_file()]


setup(
    name="mike-dotfiles",
    version="0.2.0",
    description=(
        "Cross-platform dotfiles for macOS, Linux, HPC, Codespaces, and Code Ocean"
    ),
    long_description=(Path(__file__).parent / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="Michael S. Cuoco",
    author_email="mikecuoco@users.noreply.github.com",
    license="MIT",
    python_requires=">=3.8",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"dotfiles": resource_files()},
    install_requires=["tomli>=2.0.1; python_version < '3.11'"],
    entry_points={"console_scripts": ["dotfiles=dotfiles.cli:main"]},
    zip_safe=False,
)
