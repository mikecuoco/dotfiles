#!/usr/bin/env python3
"""Perform a fast, non-executing structural review of a Code Ocean capsule."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


ARM_RE = re.compile(r"^\d{2}_[a-z0-9][a-z0-9_-]*$")
FINAL_STAGES = {"finalization"}
SCRATCH_VARIABLES = (
    "TMPDIR",
    "XDG_CACHE_HOME",
    "CONDA_PKGS_DIRS",
    "CONDA_ENVS_PATH",
    "MAMBA_ROOT_PREFIX",
    "PIP_CACHE_DIR",
    "UV_CACHE_DIR",
)
IGNORED_DIRS = {
    "__pycache__",
    "config",
    "data",
    "docs",
    "environment",
    "figures",
    "results",
    "scratch",
    "src",
    "tests",
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    path: str | None = None


def locate_layout(root: Path) -> tuple[Path, Path, Path]:
    root = root.resolve()
    if (root / "code").is_dir():
        return root, root / "code", root / "environment"
    if root.name == "code" or (root / "datasets.yaml").exists():
        capsule_root = root.parent
        return capsule_root, root, capsule_root / "environment"
    raise FileNotFoundError(f"could not locate code/ beneath {root}")


def _contains_analysis_files(directory: Path) -> bool:
    try:
        children = list(directory.iterdir())
    except OSError:
        return False
    return any(
        child.is_file()
        and (child.suffix in {".ipynb", ".r", ".R", ".jl"} or child.suffix == ".py")
        for child in children
    )


def analysis_directories(code_dir: Path) -> tuple[list[Path], list[Path]]:
    numbered: list[Path] = []
    unnumbered: list[Path] = []
    for directory in sorted(path for path in code_dir.iterdir() if path.is_dir()):
        if directory.name.startswith("."):
            continue
        if ARM_RE.fullmatch(directory.name):
            numbered.append(directory)
            continue
        if directory.name in IGNORED_DIRS or (directory / "pyproject.toml").is_file():
            continue
        if _contains_analysis_files(directory):
            unnumbered.append(directory)
    return numbered, unnumbered


def infer_stage(code_dir: Path, environment_dir: Path) -> str:
    run = code_dir / "run"
    if run.is_file():
        return "finalization"
    has_lock = any((environment_dir / name).is_file() for name in ("conda-lock.yml", "conda-lock.yaml"))
    has_scripts = any(
        path.suffix in {".py", ".r", ".R", ".jl", ".sh"}
        for directory in code_dir.iterdir()
        if directory.is_dir()
        for path in directory.iterdir()
        if path.is_file()
    )
    return "stabilization" if has_lock or has_scripts else "exploration"


def _metadata_candidates(capsule_root: Path, code_dir: Path) -> list[Path]:
    return list(
        dict.fromkeys(
            (
                capsule_root / ".codeocean" / "datasets.json",
                code_dir / ".codeocean" / "datasets.json",
            )
        )
    )


def _metadata_has_attachments(path: Path) -> bool:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    def contains_id(node: object) -> bool:
        if isinstance(node, dict):
            if any(str(node.get(key) or "").strip() for key in ("id", "data_asset_id", "dataAssetId")):
                return True
            return any(contains_id(value) for value in node.values())
        if isinstance(node, list):
            return any(contains_id(value) for value in node)
        return False

    return contains_id(document)


def review_capsule(root: Path, requested_stage: str = "auto") -> tuple[str, list[Finding]]:
    capsule_root, code_dir, environment_dir = locate_layout(root)
    stage = infer_stage(code_dir, environment_dir) if requested_stage == "auto" else requested_stage
    finalizing = stage in FINAL_STAGES
    findings: list[Finding] = []

    numbered, unnumbered = analysis_directories(code_dir)
    if numbered:
        findings.append(
            Finding("info", "analysis-arms", f"found {len(numbered)} numbered analysis arm(s)", str(code_dir))
        )
    else:
        findings.append(Finding("warning", "no-analysis-arms", "no numbered analysis arms found", str(code_dir)))
    for directory in unnumbered:
        findings.append(
            Finding(
                "error" if finalizing else "warning",
                "unnumbered-analysis-arm",
                "analysis directory should use a stable NN_name prefix",
                str(directory),
            )
        )

    datasets_yaml = code_dir / "datasets.yaml"
    datasets_md = code_dir / "DATASETS.md"
    metadata_has_attachments = any(
        path.is_file() and _metadata_has_attachments(path)
        for path in _metadata_candidates(capsule_root, code_dir)
    )
    if metadata_has_attachments and not datasets_yaml.is_file():
        findings.append(
            Finding(
                "error" if finalizing else "warning",
                "missing-dataset-manifest",
                "attached datasets are present but code/datasets.yaml is missing",
                str(datasets_yaml),
            )
        )
    elif datasets_yaml.is_file():
        findings.append(Finding("info", "dataset-manifest", "dataset manifest present", str(datasets_yaml)))
    if datasets_yaml.is_file() and not datasets_md.is_file():
        findings.append(
            Finding("warning", "missing-dataset-index", "DATASETS.md has not been generated", str(datasets_md))
        )

    environment_specs = [
        environment_dir / "environment.yml",
        environment_dir / "environment.yaml",
    ]
    locks = [environment_dir / "conda-lock.yml", environment_dir / "conda-lock.yaml"]
    if not any(path.is_file() for path in environment_specs):
        findings.append(
            Finding(
                "error" if finalizing else "info",
                "missing-environment-spec",
                "no environment.yml found",
                str(environment_dir),
            )
        )
    if not any(path.is_file() for path in locks):
        findings.append(
            Finding(
                "error" if finalizing else "info",
                "missing-conda-lock",
                "no conda-lock.yml found; lock once dependencies stabilize",
                str(environment_dir),
            )
        )

    run = code_dir / "run"
    if not run.is_file():
        findings.append(
            Finding(
                "error" if finalizing else "info",
                "missing-run",
                "run is not present; this is expected during exploration",
                str(run),
            )
        )
    elif not (run.stat().st_mode & stat.S_IXUSR):
        findings.append(Finding("error", "run-not-executable", "run is not executable", str(run)))
    else:
        findings.append(Finding("info", "run", "executable run entrypoint present", str(run)))

    scratch_exists = Path("/scratch").is_dir()
    code_ocean_runtime = scratch_exists or bool(os.environ.get("CODEOCEAN_DOMAIN"))
    if code_ocean_runtime:
        for variable in SCRATCH_VARIABLES:
            value = os.environ.get(variable)
            if value and not Path(value).as_posix().startswith("/scratch/"):
                findings.append(
                    Finding(
                        "warning",
                        "root-backed-runtime-path",
                        f"{variable} resolves outside /scratch: {value}",
                    )
                )

    return stage, findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="capsule or code root")
    parser.add_argument(
        "--stage",
        choices=("auto", "exploration", "stabilization", "finalization"),
        default="auto",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true", help="exit nonzero for warnings too")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        stage, findings = review_capsule(args.root, args.stage)
    except OSError as exc:
        print(f"error: {exc}")
        return 2

    counts = {severity: sum(item.severity == severity for item in findings) for severity in ("error", "warning", "info")}
    if args.format == "json":
        print(json.dumps({"stage": stage, "counts": counts, "findings": [asdict(item) for item in findings]}, indent=2))
    else:
        print(f"Capsule stage: {stage}")
        for finding in findings:
            location = f" ({finding.path})" if finding.path else ""
            print(f"[{finding.severity.upper()}] {finding.message}{location}")
        print(
            f"Summary: {counts['error']} error(s), {counts['warning']} warning(s), "
            f"{counts['info']} informational finding(s)"
        )

    if counts["error"] or (args.strict and counts["warning"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
