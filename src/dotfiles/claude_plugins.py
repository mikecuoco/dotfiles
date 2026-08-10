"""Claude Code plugin and MCP server management.

Provides idempotent install/check logic for the integrations declared in
``resources/claude/plugins.toml``.  All live Claude CLI calls are isolated to
the ``_run_claude`` helper so they can be mocked in tests.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class IntegrationSpec:
    """Specification for a single Claude Code integration."""

    name: str
    type: str           # "plugin" | "mcp-http" | "mcp-stdio"
    description: str = ""
    # plugin fields
    marketplace: str = ""
    # mcp-http field
    url: str = ""
    # mcp-stdio fields
    command: str = ""
    args: list[str] = field(default_factory=list)
    # optional auth hint shown in doctor / setup output
    auth_hint: str = ""


@dataclass
class GroupConfig:
    name: str
    description: str
    integrations: list[IntegrationSpec]


@dataclass
class PluginConfig:
    marketplaces: dict[str, str]        # alias → owner/repo
    groups: dict[str, GroupConfig]


@dataclass
class PluginStatus:
    name: str
    type: str
    installed: bool
    message: str
    auth_hint: str = ""


# ── Config loading ────────────────────────────────────────────────────────────

def load_plugin_config(resources_dir: Path) -> PluginConfig:
    """Load plugin/integration declarations from ``claude/plugins.toml``."""
    path = resources_dir / "claude" / "plugins.toml"
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    marketplaces: dict[str, str] = raw.get("marketplaces", {})

    groups: dict[str, GroupConfig] = {}
    for group_name, group_data in raw.get("groups", {}).items():
        integrations = [
            IntegrationSpec(
                name=spec["name"],
                type=spec["type"],
                description=spec.get("description", ""),
                marketplace=spec.get("marketplace", ""),
                url=spec.get("url", ""),
                command=spec.get("command", ""),
                args=list(spec.get("args", [])),
                auth_hint=spec.get("auth_hint", ""),
            )
            for spec in group_data.get("integrations", [])
        ]
        groups[group_name] = GroupConfig(
            name=group_name,
            description=group_data.get("description", ""),
            integrations=integrations,
        )

    return PluginConfig(marketplaces=marketplaces, groups=groups)


# ── Claude CLI interaction ────────────────────────────────────────────────────

def check_claude_available() -> bool:
    """Return True if the ``claude`` binary is on PATH."""
    return bool(shutil.which("claude"))


def _run_claude(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Run ``claude <args>`` and return the completed process.

    Raises ``subprocess.TimeoutExpired`` or ``OSError`` on process failure;
    callers must handle these.
    """
    return subprocess.run(
        ["claude", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _list_plugins() -> set[str]:
    """Return the set of installed plugin references (``name@marketplace`` form).

    Returns an empty set if the command fails or times out.
    """
    try:
        result = _run_claude(["plugin", "list"])
    except (subprocess.TimeoutExpired, OSError):
        return set()

    if result.returncode != 0:
        return set()

    installed: set[str] = set()
    for line in result.stdout.splitlines():
        token = line.strip().split()[0] if line.strip() else ""
        if "@" in token:
            installed.add(token)
    return installed


def _list_marketplaces() -> set[str]:
    """Return the set of registered marketplace names/aliases.

    Returns an empty set if the command fails or times out.
    """
    try:
        result = _run_claude(["plugin", "marketplace", "list"])
    except (subprocess.TimeoutExpired, OSError):
        return set()

    if result.returncode != 0:
        return set()

    names: set[str] = set()
    for line in result.stdout.splitlines():
        token = line.strip().split()[0] if line.strip() else ""
        if token:
            names.add(token)
    return names


def _list_mcp_servers() -> set[str]:
    """Return the set of configured MCP server names.

    Returns an empty set if the command fails or times out.
    """
    try:
        result = _run_claude(["mcp", "list"])
    except (subprocess.TimeoutExpired, OSError):
        return set()

    if result.returncode != 0:
        return set()

    names: set[str] = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            token = line.split()[0]
            if token:
                names.add(token)
    return names


# ── Setup ─────────────────────────────────────────────────────────────────────

def run_claude_setup(
    resources_dir: Path,
    groups: Optional[list[str]] = None,
    dry_run: bool = False,
) -> list[PluginStatus]:
    """Idempotently install the desired plugins and MCP servers.

    Args:
        resources_dir: path to the dotfiles ``resources/`` directory.
        groups:        list of group names to install (default: ``["default"]``).
        dry_run:       if True, report what would be done without executing.

    Returns:
        A list of :class:`PluginStatus` for each integration processed.
        Returns an empty list if ``claude`` is not on PATH.
    """
    if not check_claude_available():
        print(
            "  – claude CLI not found — skipping plugin setup\n"
            "    Install Claude Code first: https://claude.ai/code",
            file=sys.stderr,
        )
        return []

    if groups is None:
        groups = ["default"]

    config = load_plugin_config(resources_dir)

    # Collect integrations for the requested groups (preserve declaration order)
    integrations: list[IntegrationSpec] = []
    for group_name in groups:
        if group_name not in config.groups:
            print(
                f"  ✗ unknown plugin group: {group_name!r} "
                f"(available: {', '.join(sorted(config.groups))})",
                file=sys.stderr,
            )
            continue
        integrations.extend(config.groups[group_name].integrations)

    if not integrations:
        return []

    # ── Register required marketplaces ───────────────────────────────────────
    # Marketplaces needed by plugin-type integrations in the requested groups.
    # "claude-plugins-official" is built-in — no registration required.
    needed_markets: set[str] = {
        spec.marketplace
        for spec in integrations
        if spec.type == "plugin" and spec.marketplace not in ("", "claude-plugins-official")
    }

    if needed_markets:
        existing_markets = _list_marketplaces()
        for alias in sorted(needed_markets):
            if alias in existing_markets:
                print(f"  ✓ marketplace already registered: {alias}")
                continue
            source = config.marketplaces.get(alias)
            if not source:
                print(
                    f"  ✗ no source URL configured for marketplace {alias!r}",
                    file=sys.stderr,
                )
                continue
            if dry_run:
                print(f"  [dry] would register marketplace: {alias} → {source}")
            else:
                _register_marketplace(alias, source)

    # ── Install integrations ──────────────────────────────────────────────────
    # Fetch current state once; avoid repeated list calls.
    installed_plugins: set[str] = set() if dry_run else _list_plugins()
    configured_mcps:   set[str] = set() if dry_run else _list_mcp_servers()

    statuses: list[PluginStatus] = []
    for spec in integrations:
        status = _process_one(spec, installed_plugins, configured_mcps, dry_run)
        statuses.append(status)
        _print_status_line(status, dry_run)

    return statuses


def _register_marketplace(alias: str, source: str) -> None:
    """Register a plugin marketplace; print outcome."""
    try:
        result = _run_claude(["plugin", "marketplace", "add", source])
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"  ✗ failed to register marketplace {alias!r}: {exc}", file=sys.stderr)
        return

    if result.returncode == 0:
        print(f"  → registered marketplace: {alias}")
    else:
        err = (result.stderr or result.stdout or "unknown error").strip()[:200]
        print(f"  ✗ failed to register marketplace {alias!r}: {err}", file=sys.stderr)


def _process_one(
    spec: IntegrationSpec,
    installed_plugins: set[str],
    configured_mcps: set[str],
    dry_run: bool,
) -> PluginStatus:
    """Determine whether to install/configure *spec* and do so if needed."""
    match spec.type:
        case "plugin":
            return _process_plugin(spec, installed_plugins, dry_run)
        case "mcp-http":
            return _process_mcp_http(spec, configured_mcps, dry_run)
        case "mcp-stdio":
            return _process_mcp_stdio(spec, configured_mcps, dry_run)
        case _:
            return PluginStatus(
                spec.name, spec.type, False,
                f"unsupported integration type: {spec.type!r}",
                spec.auth_hint,
            )


def _process_plugin(
    spec: IntegrationSpec,
    installed_plugins: set[str],
    dry_run: bool,
) -> PluginStatus:
    ref = f"{spec.name}@{spec.marketplace}"
    if ref in installed_plugins:
        return PluginStatus(spec.name, spec.type, True, "already installed", spec.auth_hint)

    if dry_run:
        return PluginStatus(spec.name, spec.type, False, "would install", spec.auth_hint)

    try:
        result = _run_claude(["plugin", "install", ref, "--scope", "user"])
    except (subprocess.TimeoutExpired, OSError) as exc:
        return PluginStatus(spec.name, spec.type, False, f"install failed: {exc}", spec.auth_hint)

    if result.returncode == 0:
        return PluginStatus(spec.name, spec.type, True, "installed", spec.auth_hint)

    err = (result.stderr or result.stdout or "unknown error").strip()[:200]
    return PluginStatus(spec.name, spec.type, False, f"install failed: {err}", spec.auth_hint)


def _process_mcp_http(
    spec: IntegrationSpec,
    configured_mcps: set[str],
    dry_run: bool,
) -> PluginStatus:
    if spec.name in configured_mcps:
        return PluginStatus(spec.name, spec.type, True, "already configured", spec.auth_hint)

    if dry_run:
        return PluginStatus(spec.name, spec.type, False, "would configure", spec.auth_hint)

    try:
        result = _run_claude([
            "mcp", "add",
            "--transport", "http",
            "--scope", "user",
            spec.name, spec.url,
        ])
    except (subprocess.TimeoutExpired, OSError) as exc:
        return PluginStatus(spec.name, spec.type, False, f"mcp add failed: {exc}", spec.auth_hint)

    if result.returncode == 0:
        return PluginStatus(spec.name, spec.type, True, "configured", spec.auth_hint)

    err = (result.stderr or result.stdout or "unknown error").strip()[:200]
    return PluginStatus(spec.name, spec.type, False, f"mcp add failed: {err}", spec.auth_hint)


def _process_mcp_stdio(
    spec: IntegrationSpec,
    configured_mcps: set[str],
    dry_run: bool,
) -> PluginStatus:
    if spec.name in configured_mcps:
        return PluginStatus(spec.name, spec.type, True, "already configured", spec.auth_hint)

    if dry_run:
        return PluginStatus(spec.name, spec.type, False, "would configure", spec.auth_hint)

    # Check that the required binary is on PATH before attempting to register it.
    if not shutil.which(spec.command):
        return PluginStatus(
            spec.name, spec.type, False,
            f"command not found: {spec.command!r} — install it first",
            spec.auth_hint,
        )

    cmd_args = [
        "mcp", "add",
        "--transport", "stdio",
        "--scope", "user",
        spec.name,
        "--",
        spec.command,
        *spec.args,
    ]
    try:
        result = _run_claude(cmd_args)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return PluginStatus(spec.name, spec.type, False, f"mcp add failed: {exc}", spec.auth_hint)

    if result.returncode == 0:
        return PluginStatus(spec.name, spec.type, True, "configured", spec.auth_hint)

    err = (result.stderr or result.stdout or "unknown error").strip()[:200]
    return PluginStatus(spec.name, spec.type, False, f"mcp add failed: {err}", spec.auth_hint)


def _print_status_line(status: PluginStatus, dry_run: bool) -> None:
    """Print one line of setup progress output."""
    would = dry_run and status.message.startswith("would ")

    if status.installed or would:
        icon = "→" if status.message in ("installed", "configured") else "✓"
        if would:
            print(f"  [dry] {icon} {status.name}: {status.message}")
        else:
            print(f"  {icon} {status.name}: {status.message}")
        if status.auth_hint:
            print(f"      auth: {status.auth_hint}")
    else:
        print(f"  ✗ {status.name}: {status.message}", file=sys.stderr)
        if status.auth_hint:
            print(f"      auth needed: {status.auth_hint}", file=sys.stderr)


# ── Read-only status (used by doctor) ─────────────────────────────────────────

def check_plugin_statuses(
    resources_dir: Path,
    groups: Optional[list[str]] = None,
) -> list[PluginStatus]:
    """Return current install status for integrations without modifying anything.

    Used by ``dotfiles doctor``.  Returns an empty list when ``claude`` is not
    on PATH (not an error for doctor purposes).
    """
    if not check_claude_available():
        return []

    if groups is None:
        groups = ["default", "bioinformatics"]

    config = load_plugin_config(resources_dir)
    installed_plugins = _list_plugins()
    configured_mcps   = _list_mcp_servers()

    statuses: list[PluginStatus] = []
    for group_name in groups:
        if group_name not in config.groups:
            continue
        for spec in config.groups[group_name].integrations:
            match spec.type:
                case "plugin":
                    ref = f"{spec.name}@{spec.marketplace}"
                    is_ok = ref in installed_plugins
                    msg   = "installed" if is_ok else "not installed"
                case "mcp-http" | "mcp-stdio":
                    is_ok = spec.name in configured_mcps
                    msg   = "configured" if is_ok else "not configured"
                case _:
                    is_ok, msg = False, f"unknown type {spec.type!r}"
            statuses.append(PluginStatus(spec.name, spec.type, is_ok, msg, spec.auth_hint))

    return statuses
