"""Dotfiles health-check command."""
from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .auth import AuthStatus, all_statuses
from .claude_plugins import PluginStatus, check_plugin_statuses
from .claude_skills import SkillStatus, check_skill_statuses
from .install import get_resources_dir, read_state
from .platform import PlatformInfo, detect_platform


# Tools to check — split into required and optional
_REQUIRED_TOOLS = ("git", "python3")
_OPTIONAL_TOOLS = ("uv", "gh", "aws", "claude", "delta", "fzf", "eza", "rg", "vim")


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
    # Claude skills section — first-party managed directories and bio-* files
    skill_statuses: list[SkillStatus] = field(default_factory=list)


def run_doctor(as_json: bool = False) -> int:
    """Run all checks and print a status report.  Returns exit code."""
    home = Path.home()
    resources = get_resources_dir()
    platform_info = detect_platform()
    state = read_state(home)

    report = DoctorReport(
        platform=platform_info,
        profile=state["profile"] if state else None,
        dotfiles_ok=state is not None,
    )

    # ── File checks ──────────────────────────────────────────────────────────
    if state:
        for dst_rel, src_rel in state["links"].items():
            dst = home / dst_rel
            src = resources / src_rel
            if dst.is_symlink():
                try:
                    if dst.resolve() == src.resolve():
                        report.file_statuses.append(
                            FileStatus(dst_rel, True, "ok")
                        )
                        continue
                except OSError:
                    pass
                report.file_statuses.append(
                    FileStatus(dst_rel, False, "symlink points elsewhere")
                )
            elif dst.exists():
                report.file_statuses.append(
                    FileStatus(dst_rel, False, "exists but not a dotfiles symlink")
                )
            else:
                report.file_statuses.append(
                    FileStatus(dst_rel, False, "missing")
                )

    # ── Tool checks ──────────────────────────────────────────────────────────
    for name in _REQUIRED_TOOLS:
        path = shutil.which(name)
        report.tool_statuses.append(ToolStatus(name, bool(path), path, required=True))
    for name in _OPTIONAL_TOOLS:
        path = shutil.which(name)
        report.tool_statuses.append(ToolStatus(name, bool(path), path, required=False))

    # ── Auth checks ──────────────────────────────────────────────────────────
    report.auth_statuses = all_statuses()

    # ── Claude plugin checks ──────────────────────────────────────────────────
    # Non-fatal: if claude CLI is absent, both lists remain empty and the
    # section is omitted from the output.
    all_plugin_statuses = check_plugin_statuses(resources)
    report.claude_plugin_statuses = [
        s for s in all_plugin_statuses
        if _is_default_plugin(s, resources)
    ]
    report.bio_plugin_statuses = [
        s for s in all_plugin_statuses
        if not _is_default_plugin(s, resources)
    ]

    # ── Claude skill checks ───────────────────────────────────────────────────
    # Non-fatal: warn if none are installed; not an error for exit-code purposes.
    report.skill_statuses = check_skill_statuses(home / ".claude" / "skills")

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

    if not report.dotfiles_ok or broken_files or missing_required_tools:
        return 1
    if missing_required_auth:
        return 1
    return 0


# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_default_plugin(status: PluginStatus, resources: Path) -> bool:
    """Return True if *status* belongs to the default plugin group."""
    from .claude_plugins import load_plugin_config
    try:
        cfg = load_plugin_config(resources)
        default_names = {s.name for s in cfg.groups.get("default", _empty_group()).integrations}
        return status.name in default_names
    except (FileNotFoundError, KeyError):
        return False


def _empty_group():
    from .claude_plugins import GroupConfig
    return GroupConfig(name="", description="", integrations=[])


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
        broken = [f for f in report.file_statuses if not f.installed]
        good   = [f for f in report.file_statuses if f.installed]
        if not broken:
            print(ok(f"All {len(good)} files installed correctly"))
        else:
            print(ok(f"{len(good)} files ok"))
            for fs in broken:
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

    print("\nClaude skills")
    if not report.skill_statuses:
        print(warn("no managed skills installed — run: dotfiles skills install"))
    else:
        from collections import Counter
        by_cat = Counter(s.category for s in report.skill_statuses)
        total = len(report.skill_statuses)
        print(ok(f"{total} skill(s) installed across {len(by_cat)} category(ies)"))
        for cat, count in sorted(by_cat.items()):
            print(f"      {cat:<28} {count}")

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
        "tools": [
            {
                "name": t.name,
                "found": t.found,
                "path": t.path,
                "required": t.required,
            }
            for t in report.tool_statuses
        ],
        "auth": [
            {
                "name": a.name,
                "configured": a.configured,
                "message": a.message,
                "required": a.required,
            }
            for a in report.auth_statuses
        ],
        "claude_plugins": [
            {
                "name": p.name,
                "type": p.type,
                "installed": p.installed,
                "message": p.message,
                "auth_hint": p.auth_hint,
            }
            for p in report.claude_plugin_statuses
        ],
        "bio_plugins": [
            {
                "name": p.name,
                "type": p.type,
                "installed": p.installed,
                "message": p.message,
                "auth_hint": p.auth_hint,
            }
            for p in report.bio_plugin_statuses
        ],
        "bioskills": [
            {
                "name": s.name,
                "category": s.category,
                "installed": s.installed,
                "message": s.message,
            }
            for s in report.skill_statuses
        ],
    }
    print(json.dumps(data, indent=2))
