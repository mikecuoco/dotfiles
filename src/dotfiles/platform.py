"""Platform and environment detection."""
from __future__ import annotations

import os
import platform
import socket
from dataclasses import dataclass, field
from typing import Literal

Platform = Literal["macos", "linux", "cluster", "codeocean", "codespace"]

VALID_PROFILES: frozenset[str] = frozenset(
    {"macos", "linux", "cluster", "codeocean", "codespace"}
)

# Keywords in hostnames that suggest an HPC cluster login node
_CLUSTER_HOST_KEYWORDS = (
    "login", "head", "compute", "node", "hpc", "cluster",
    "slurm", "tscc", "comet", "expanse", "stampede", "bridges",
    "sherlock", "frontier", "summit", "pbs",
)


@dataclass
class PlatformInfo:
    platform: str  # one of Platform literals
    os_name: str   # "Darwin" | "Linux" | …
    hostname: str
    signals: list[str] = field(default_factory=list)


def detect_platform(override: str | None = None) -> PlatformInfo:
    """Detect the current platform.

    Detection order (first match wins):

    1. ``override`` / ``--profile`` flag
    2. ``CODESPACES=true``       → codespace
    3. Code Ocean runtime variables present → codeocean
    4. SLURM / PBS / SGE env vars or cluster-like hostname → cluster
    5. Linux (no above signals)  → linux
    6. Darwin                    → macos
    """
    os_name = platform.system()          # "Darwin" | "Linux" | "Windows" | …
    hostname = socket.gethostname().lower()

    if override:
        if override not in VALID_PROFILES:
            valid = ", ".join(sorted(VALID_PROFILES))
            raise ValueError(
                f"Unknown profile '{override}'. Valid profiles: {valid}"
            )
        return PlatformInfo(
            platform=override,
            os_name=os_name,
            hostname=hostname,
            signals=[f"--profile {override} (explicit)"],
        )

    env = os.environ

    # ── Codespaces ──────────────────────────────────────────────────────────
    if env.get("CODESPACES") == "true" or env.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"):
        return PlatformInfo("codespace", os_name, hostname, ["CODESPACES=true"])

    # ── Code Ocean ──────────────────────────────────────────────────────────
    # CO_CAPSULE_ID / CO_PIPELINE_ID and CO_COMPUTATION_ID are the documented
    # runtime variables. Keep the older signals for existing deployments.
    codeocean_vars = (
        "CO_CAPSULE_ID",
        "CO_PIPELINE_ID",
        "CO_COMPUTATION_ID",
        "CODEOCEAN_ENV",
        "CO_REPO_ID",
    )
    codeocean_signals = [f"{var} set" for var in codeocean_vars if env.get(var)]
    if codeocean_signals:
        return PlatformInfo("codeocean", os_name, hostname, codeocean_signals)

    # ── HPC Cluster ─────────────────────────────────────────────────────────
    cluster_sigs: list[str] = []
    for var in ("SLURM_JOB_ID", "PBS_JOBID", "SGE_TASK_ID", "LSB_JOBID"):
        if env.get(var):
            cluster_sigs.append(f"{var} set")
    if any(kw in hostname for kw in _CLUSTER_HOST_KEYWORDS):
        cluster_sigs.append(f"hostname contains cluster keyword: {hostname}")
    if cluster_sigs:
        return PlatformInfo("cluster", os_name, hostname, cluster_sigs)

    # ── OS-based fallback ────────────────────────────────────────────────────
    if os_name == "Linux":
        return PlatformInfo("linux", os_name, hostname, ["uname=Linux"])
    if os_name == "Darwin":
        return PlatformInfo("macos", os_name, hostname, ["uname=Darwin"])

    # Unknown OS — fall back to linux behaviour
    return PlatformInfo(
        "linux", os_name, hostname,
        [f"uname={os_name} (unknown; defaulting to linux)"],
    )
