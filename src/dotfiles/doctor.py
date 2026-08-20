"""Dotfiles health-check command."""
from __future__ import annotations

import json
import shutil
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from . import RESOURCES_DIR, chezmoi
from .auth import AuthStatus, all_statuses
from .claude_plugins import PluginStatus, check_plugin_statuses, load_plugin_config
from .agent_skills import SkillStatus, check_skill_statuses
from .install import claude_skills_dir
from .platform import PlatformInfo, detect_platform
from .project_memory import MemoryStatus, check_project_memory, find_repo_root


# Tools to check — split into required and optional
_REQUIRED_TOOLS = ("git", "python3")
_OPTIONAL_TOOLS = (
    "uv", "gh", "aws", "claude", "codex", "delta", "fzf", "eza", "rg", "vim",
)


def _which(name: str) -> Optional[str]:
    """Locate a tool on PATH.

    Indirection on purpose: tests fake tool discovery here, and patching
    ``shutil.which`` wholesale would also blind the chezmoi wrapper, which
    needs to find its own binary.
    """
    return shutil.which(name)


@dataclass
class ToolStatus:
    name: str
    found: bool
    path: Optional[str]
    required: bool


@dataclass
class FileStatus:
    rel_path: str
    installed: bool
    message: str

    @classmethod
    def from_chezmoi(cls, line: str) -> "FileStatus":
        """Parse one ``chezmoi status`` line.

        The format mirrors ``git status --short``: two status columns then the
        path. Column two is what apply would do -- A(dd), M(odify), D(elete).
        """
        codes, _, path = line.partition(" ")
        return cls(path.strip(), False, _STATUS_MESSAGES.get(
            codes.strip()[-1:], f"would change ({codes.strip()})"
        ))


_STATUS_MESSAGES = {
    "A": "missing -- would be created",
    "M": "differs from the managed version",
    "D": "no longer managed -- would be removed",
}


@dataclass
class DoctorReport:
    platform: PlatformInfo
    profile: Optional[str]
    dotfiles_ok: bool
    file_statuses: list[FileStatus] = field(default_factory=list)
    tool_statuses: list[ToolStatus] = field(default_factory=list)
    auth_statuses: list[AuthStatus] = field(default_factory=list)
    # Claude plugin sections — populated only when `claude` CLI is on PATH
    claude_plugin_statuses: list[PluginStatus] = field(default_factory=list)
    bio_plugin_statuses: list[PluginStatus] = field(default_factory=list)
    # Agent skills — first-party managed directories and bio-* files
    skill_statuses: list[SkillStatus] = field(default_factory=list)
    codex_skill_statuses: list[SkillStatus] = field(default_factory=list)
    project_memory_root: Optional[str] = None
    project_memory_statuses: list[MemoryStatus] = field(default_factory=list)


def run_doctor(as_json: bool = False) -> int:
    """Run all checks and print a status report.  Returns exit code."""
    home = Path.home()
    resources = RESOURCES_DIR
    platform_info = detect_platform()
    installed_profile = chezmoi.active_profile()

    # Some deployed containers omit their platform's usual runtime variables.
    # A specialized profile saved by an explicit install is better evidence
    # than the generic Linux fallback in that case.
    if (
        installed_profile
        and platform_info.platform == "linux"
        and installed_profile in {"cluster", "codeocean", "codespace"}
    ):
        platform_info = PlatformInfo(
            installed_profile,
            platform_info.os_name,
            platform_info.hostname,
            [f"installed profile={installed_profile}"],
        )

    report = DoctorReport(
        platform=platform_info,
        profile=installed_profile,
        dotfiles_ok=installed_profile is not None,
    )

    # ── File checks ──────────────────────────────────────────────────────────
    # chezmoi compares its target state against the destination directly, so
    # there is no separate manifest to drift out of sync with reality.
    if installed_profile:
        try:
            report.file_statuses = [
                FileStatus.from_chezmoi(line) for line in chezmoi.status()
            ]
        except chezmoi.ChezmoiError as exc:
            report.file_statuses = [FileStatus("(chezmoi status)", False, str(exc))]

    # ── Tool checks ──────────────────────────────────────────────────────────
    for name in _REQUIRED_TOOLS:
        path = _which(name)
        report.tool_statuses.append(ToolStatus(name, bool(path), path, required=True))
    for name in _OPTIONAL_TOOLS:
        path = _which(name)
        report.tool_statuses.append(ToolStatus(name, bool(path), path, required=False))

    # ── Auth checks ──────────────────────────────────────────────────────────
    report.auth_statuses = all_statuses()

    # ── Claude plugin checks ──────────────────────────────────────────────────
    # Non-fatal: if claude CLI is absent, both lists remain empty and the
    # section is omitted from the output.
    all_plugin_statuses = check_plugin_statuses(resources)
    default_names = _default_plugin_names(resources)
    for status in all_plugin_statuses:
        if status.name in default_names:
            report.claude_plugin_statuses.append(status)
        else:
            report.bio_plugin_statuses.append(status)

    # ── Agent skill checks ────────────────────────────────────────────────────
    # Non-fatal: warn if none are installed; not an error for exit-code purposes.
    report.skill_statuses = check_skill_statuses(claude_skills_dir(home))
    report.codex_skill_statuses = check_skill_statuses(home / ".agents" / "skills")

    # ── Shared project memory ────────────────────────────────────────────────
    memory_root = find_repo_root(Path.cwd())
    report.project_memory_root = str(memory_root)
    report.project_memory_statuses = check_project_memory(memory_root)

    # ── Output ──────────────────────────────────────────────────────────────
    if as_json:
        _emit_json(report)
    else:
        _emit_human(report)

    # Determine exit code
    broken_files = any(not f.installed for f in report.file_statuses)
    missing_required_tools = any(
        not t.found for t in report.tool_statuses if t.required
    )
    missing_required_auth = any(
        not a.configured for a in report.auth_statuses if a.required
    )
    broken_project_memory = any(
        not status.ok for status in report.project_memory_statuses
    )

    if (
        not report.dotfiles_ok
        or broken_files
        or missing_required_tools
        or broken_project_memory
    ):
        return 1
    if missing_required_auth:
        return 1
    return 0


# ── Internal helpers ──────────────────────────────────────────────────────────

def _default_plugin_names(resources: Path) -> set[str]:
    """Return the integration names in the ``default`` plugin group.

    Loaded once per doctor run; an unreadable config classifies everything as
    non-default, matching the previous per-status fallback.
    """
    try:
        cfg = load_plugin_config(resources)
    except (FileNotFoundError, KeyError):
        return set()
    group = cfg.groups.get("default")
    return {spec.name for spec in group.integrations} if group else set()


# ── Formatters ────────────────────────────────────────────────────────────────

def _emit_human(report: DoctorReport) -> None:
    def ok(msg: str) -> str:  return f"  \033[32m✓\033[0m {msg}"
    def warn(msg: str) -> str: return f"  \033[33m–\033[0m {msg}"
    def fail(msg: str) -> str: return f"  \033[31m✗\033[0m {msg}"

    print("Platform")
    print(ok(f"{report.platform.os_name}  ({report.platform.hostname})"))
    for sig in report.platform.signals:
        print(ok(sig))

    print("\nDotfiles")
    if not report.dotfiles_ok:
        print(fail("Not installed — run: dotfiles install"))
    else:
        print(ok(f"Profile: {report.profile}"))
        # chezmoi reports discrepancies only; an empty list means everything
        # in the target state matches the destination.
        if not report.file_statuses:
            print(ok("All managed files are up to date"))
        else:
            print(fail(f"{len(report.file_statuses)} file(s) out of date"))
            for fs in report.file_statuses:
                print(fail(f"{fs.rel_path}: {fs.message}"))

    print("\nTools")
    for ts in report.tool_statuses:
        if ts.found:
            print(ok(ts.name))
        elif ts.required:
            print(fail(f"{ts.name} not found (required)"))
        else:
            print(warn(f"{ts.name} not found (optional)"))

    print("\nAuthentication")
    for auth in report.auth_statuses:
        if auth.configured:
            print(ok(auth.name))
        elif auth.required:
            print(fail(f"{auth.name}: {auth.message}"))
        else:
            print(warn(f"{auth.name}: {auth.message}"))

    if report.claude_plugin_statuses or report.bio_plugin_statuses:
        print("\nClaude integrations")
        for ps in report.claude_plugin_statuses:
            _print_plugin_status(ps, ok, warn, fail)

    if report.bio_plugin_statuses:
        print("\nBioinformatics integrations")
        for ps in report.bio_plugin_statuses:
            _print_plugin_status(ps, ok, warn, fail)

    for label, statuses in (
        ("Claude Code skills", report.skill_statuses),
        ("Codex skills", report.codex_skill_statuses),
    ):
        print(f"\n{label}")
        if not statuses:
            print(warn("no managed skills installed — run: dotfiles install"))
            continue
        by_cat = Counter(s.category for s in statuses)
        total = len(statuses)
        print(ok(f"{total} skill(s) installed across {len(by_cat)} category(ies)"))
        for cat, count in sorted(by_cat.items()):
            print(f"      {cat:<28} {count}")

    print("\nProject memory")
    print(f"      root: {report.project_memory_root}")
    for status in report.project_memory_statuses:
        message = f"{status.path}: {status.message}"
        if status.level == "error":
            print(fail(message))
        elif status.level == "warning":
            print(warn(message))
        elif status.level == "info":
            print(warn(message))
        else:
            print(ok(message))

    print()


def _print_plugin_status(ps: PluginStatus, ok, warn, fail) -> None:
    label = f"{ps.name} ({ps.type})"
    if ps.installed:
        line = ok(label)
        if ps.auth_hint:
            line += f"  \033[33m— auth: {ps.auth_hint}\033[0m"
        print(line)
    else:
        print(warn(f"{label}: {ps.message}"))
        if ps.auth_hint:
            print(f"      auth needed: {ps.auth_hint}")


def _emit_json(report: DoctorReport) -> None:
    data = {
        "platform": {
            "name": report.platform.platform,
            "os": report.platform.os_name,
            "hostname": report.platform.hostname,
            "signals": report.platform.signals,
        },
        "dotfiles": {
            "installed": report.dotfiles_ok,
            "profile": report.profile,
            "files": [
                {"path": f.rel_path, "ok": f.installed, "message": f.message}
                for f in report.file_statuses
            ],
        },
        # These four status types already name their fields exactly as the
        # JSON contract does, so asdict() is the schema.
        "tools": [asdict(t) for t in report.tool_statuses],
        "auth": [asdict(a) for a in report.auth_statuses],
        "claude_plugins": [asdict(p) for p in report.claude_plugin_statuses],
        "bio_plugins": [asdict(p) for p in report.bio_plugin_statuses],
        "bioskills": [asdict(s) for s in report.skill_statuses],
        "codex_skills": [asdict(s) for s in report.codex_skill_statuses],
        "project_memory": {
            "root": report.project_memory_root,
            # `ok` is a computed property rather than a field, so this one is
            # spelled out — key order is part of the emitted contract.
            "checks": [
                {
                    "path": status.path,
                    "level": status.level,
                    "ok": status.ok,
                    "message": status.message,
                }
                for status in report.project_memory_statuses
            ],
        },
    }
    print(json.dumps(data, indent=2))
