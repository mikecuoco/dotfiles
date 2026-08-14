"""Version-independent access to the standard-library TOML parser."""
from __future__ import annotations

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # Python 3.8–3.10
    import tomli as tomllib
