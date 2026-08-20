"""Tests for Claude Code plugin and MCP server management.

All subprocess calls to the claude CLI are mocked so these tests run
without network access or a live claude installation.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from dotfiles.claude_plugins import (
    GroupConfig,
    IntegrationSpec,
    PluginStatus,
    check_plugin_statuses,
    load_plugin_config,
    run_claude_setup,
)
from dotfiles import RESOURCES_DIR

RESOURCES = RESOURCES_DIR

# ── Config loading ────────────────────────────────────────────────────────────

def test_config_loads_without_error():
    """plugins.toml parses without exception."""
    cfg = load_plugin_config(RESOURCES)
    assert cfg.groups
    assert cfg.marketplaces


def test_marketplaces_declared():
    cfg = load_plugin_config(RESOURCES)
    assert "life-sciences" in cfg.marketplaces
    assert cfg.marketplaces["life-sciences"] == "anthropics/life-sciences"


def test_default_group_exists():
    cfg = load_plugin_config(RESOURCES)
    assert "default" in cfg.groups


def test_bioinformatics_group_exists():
    cfg = load_plugin_config(RESOURCES)
    assert "bioinformatics" in cfg.groups


def test_default_group_members():
    """All required default integrations are present."""
    cfg = load_plugin_config(RESOURCES)
    names = {s.name for s in cfg.groups["default"].integrations}
    assert "github" in names
    assert "pubmed" in names
    assert "synapse" in names
    assert "context7" in names
    assert "pyright-lsp" in names


def test_bioinformatics_group_members():
    """All required bioinformatics integrations are present."""
    cfg = load_plugin_config(RESOURCES)
    names = {s.name for s in cfg.groups["bioinformatics"].integrations}
    assert "biorxiv" in names
    assert "open-targets" in names
    assert "tooluniverse" in names
    assert "scvi-tools" in names
    assert "single-cell-rna-qc" in names
    assert "nextflow-development" in names
    assert "scientific-problem-selection" in names


def test_excluded_plugins_absent_from_default():
    """Explicitly excluded plugins must not appear in the default group."""
    cfg = load_plugin_config(RESOURCES)
    names = {s.name for s in cfg.groups["default"].integrations}
    assert "10x-genomics" not in names
    assert "chembl" not in names
    assert "consensus" not in names


def test_excluded_plugins_absent_from_bioinformatics():
    """Explicitly excluded plugins must not appear in the bioinformatics group."""
    cfg = load_plugin_config(RESOURCES)
    names = {s.name for s in cfg.groups["bioinformatics"].integrations}
    assert "10x-genomics" not in names
    assert "chembl" not in names
    assert "consensus" not in names


def test_excluded_plugins_absent_from_all_groups():
    """Excluded plugins must not appear in any group."""
    cfg = load_plugin_config(RESOURCES)
    all_names = {
        s.name
        for group in cfg.groups.values()
        for s in group.integrations
    }
    assert "10x-genomics" not in all_names
    assert "chembl" not in all_names
    assert "consensus" not in all_names


def test_integration_types_are_valid():
    """All integrations declare a recognised type."""
    valid_types = {"plugin", "mcp-http", "mcp-stdio"}
    cfg = load_plugin_config(RESOURCES)
    for group in cfg.groups.values():
        for spec in group.integrations:
            assert spec.type in valid_types, (
                f"{spec.name} has unknown type {spec.type!r}"
            )


def test_plugin_integrations_have_marketplace():
    """plugin-type integrations must declare a marketplace."""
    cfg = load_plugin_config(RESOURCES)
    for group in cfg.groups.values():
        for spec in group.integrations:
            if spec.type == "plugin":
                assert spec.marketplace, (
                    f"{spec.name} is type='plugin' but has no marketplace"
                )


def test_mcp_http_integrations_have_url():
    cfg = load_plugin_config(RESOURCES)
    for group in cfg.groups.values():
        for spec in group.integrations:
            if spec.type == "mcp-http":
                assert spec.url.startswith("http"), (
                    f"{spec.name} mcp-http has invalid url: {spec.url!r}"
                )


def test_mcp_stdio_integrations_have_command():
    cfg = load_plugin_config(RESOURCES)
    for group in cfg.groups.values():
        for spec in group.integrations:
            if spec.type == "mcp-stdio":
                assert spec.command, (
                    f"{spec.name} is type='mcp-stdio' but has no command"
                )


def test_context7_is_mcp_http():
    cfg = load_plugin_config(RESOURCES)
    specs = {s.name: s for s in cfg.groups["default"].integrations}
    assert specs["context7"].type == "mcp-http"
    assert "context7.com" in specs["context7"].url


def test_tooluniverse_is_mcp_stdio():
    cfg = load_plugin_config(RESOURCES)
    specs = {s.name: s for s in cfg.groups["bioinformatics"].integrations}
    assert specs["tooluniverse"].type == "mcp-stdio"
    assert specs["tooluniverse"].command == "tooluniverse"


# ── run_claude_setup — claude not available ───────────────────────────────────

def test_setup_returns_empty_when_claude_not_on_path(capsys):
    with patch("dotfiles.claude_plugins.shutil.which", return_value=None):
        result = run_claude_setup(RESOURCES)
    assert result == []
    captured = capsys.readouterr()
    assert "claude CLI not found" in captured.err


# ── run_claude_setup — dry run ────────────────────────────────────────────────

def _make_completed(returncode=0, stdout="", stderr=""):
    m = MagicMock(spec=subprocess.CompletedProcess)
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_dry_run_makes_no_subprocess_write_calls(capsys):
    """In dry-run mode no plugin install or mcp add calls are made."""
    with patch("dotfiles.claude_plugins.shutil.which", return_value="/usr/bin/claude"), \
         patch("dotfiles.claude_plugins._run_claude") as mock_run:
        # Any 'list' calls that fire during dry-run return empty
        mock_run.return_value = _make_completed(returncode=0, stdout="")
        run_claude_setup(RESOURCES, groups=["default"], dry_run=True)

    # In dry-run we still call list commands (marketplace list, plugin list, mcp
    # list) — but must NOT call plugin install or mcp add.
    install_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][:2] == ["plugin", "install"]
        or c.args[0][:2] == ["mcp", "add"]
    ]
    assert install_calls == [], f"Unexpected write calls in dry-run: {install_calls}"


def test_dry_run_output_contains_would(capsys):
    with patch("dotfiles.claude_plugins.shutil.which", return_value="/usr/bin/claude"), \
         patch("dotfiles.claude_plugins._run_claude",
               return_value=_make_completed(stdout="")):
        run_claude_setup(RESOURCES, groups=["default"], dry_run=True)

    captured = capsys.readouterr()
    assert "would" in captured.out or "[dry]" in captured.out


# ── run_claude_setup — skip already-installed ─────────────────────────────────

def test_setup_skips_already_installed_plugin(capsys):
    """If claude plugin list already shows the plugin, skip install."""
    # Simulate all default plugins already installed
    plugin_list_output = (
        "github@claude-plugins-official\n"
        "pubmed@life-sciences\n"
        "synapse@life-sciences\n"
        "pyright-lsp@claude-plugins-official\n"
    )
    mcp_list_output = "context7\n"
    marketplace_list_output = "life-sciences\n"

    def fake_run(args, timeout=30):
        cmd = args[0] if args else ""
        sub = args[1] if len(args) > 1 else ""
        sub2 = args[2] if len(args) > 2 else ""
        if cmd == "plugin" and sub == "list":
            return _make_completed(stdout=plugin_list_output)
        if cmd == "plugin" and sub == "marketplace" and sub2 == "list":
            return _make_completed(stdout=marketplace_list_output)
        if cmd == "mcp" and sub == "list":
            return _make_completed(stdout=mcp_list_output)
        return _make_completed(stdout="")

    with patch("dotfiles.claude_plugins.shutil.which", return_value="/usr/bin/claude"), \
         patch("dotfiles.claude_plugins._run_claude", side_effect=fake_run) as mock_run:
        statuses = run_claude_setup(RESOURCES, groups=["default"])

    install_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][:2] == ["plugin", "install"]
    ]
    assert install_calls == [], "Should not install already-present plugins"

    mcp_add_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][:2] == ["mcp", "add"]
    ]
    assert mcp_add_calls == [], "Should not add already-configured MCP servers"


def test_setup_installs_missing_plugin(capsys):
    """If a plugin is not in the list, install it."""
    def fake_run(args, timeout=30):
        cmd, sub = args[0], args[1] if len(args) > 1 else ""
        sub2 = args[2] if len(args) > 2 else ""
        if cmd == "plugin" and sub == "list":
            return _make_completed(stdout="")  # nothing installed
        if cmd == "plugin" and sub == "marketplace" and sub2 == "list":
            return _make_completed(stdout="life-sciences\n")
        if cmd == "mcp" and sub == "list":
            return _make_completed(stdout="")
        if cmd == "plugin" and sub == "install":
            return _make_completed(stdout="installed\n")
        if cmd == "mcp" and sub == "add":
            return _make_completed(stdout="added\n")
        return _make_completed(stdout="")

    with patch("dotfiles.claude_plugins.shutil.which", return_value="/usr/bin/claude"), \
         patch("dotfiles.claude_plugins._run_claude", side_effect=fake_run) as mock_run:
        statuses = run_claude_setup(RESOURCES, groups=["default"])

    install_calls = [
        c.args[0] for c in mock_run.call_args_list
        if c.args[0][:2] == ["plugin", "install"]
    ]
    # Synapse requires ~/.synapseConfig, so it is skipped when that optional
    # local configuration is absent. The remaining plugin integrations install.
    assert len(install_calls) >= 3


def test_setup_idempotent(capsys):
    """Running setup twice when everything is already installed makes zero installs."""
    # Simulate: all default plugins already installed, context7 already configured.
    plugin_list_output = (
        "github@claude-plugins-official\n"
        "pubmed@life-sciences\n"
        "synapse@life-sciences\n"
        "pyright-lsp@claude-plugins-official\n"
    )
    mcp_list_output = "context7\n"

    def fake_run(args, timeout=30):
        cmd, sub = args[0], args[1] if len(args) > 1 else ""
        sub2 = args[2] if len(args) > 2 else ""
        if cmd == "plugin" and sub == "list":
            return _make_completed(stdout=plugin_list_output)
        if cmd == "plugin" and sub == "marketplace" and sub2 == "list":
            return _make_completed(stdout="life-sciences\n")
        if cmd == "mcp" and sub == "list":
            return _make_completed(stdout=mcp_list_output)
        # Should never reach here in idempotent run
        return _make_completed(stdout="")

    with patch("dotfiles.claude_plugins.shutil.which", return_value="/usr/bin/claude"), \
         patch("dotfiles.claude_plugins._run_claude", side_effect=fake_run) as mock_run:
        run_claude_setup(RESOURCES, groups=["default"])

    install_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][:2] in (["plugin", "install"], ["mcp", "add"])
    ]
    assert install_calls == [], (
        "When all plugins are already installed, setup must make zero install calls"
    )


# ── run_claude_setup — marketplace registration ───────────────────────────────

def test_marketplace_registered_if_missing():
    """If life-sciences marketplace not listed, register it before install."""
    def fake_run(args, timeout=30):
        cmd, sub = args[0], args[1] if len(args) > 1 else ""
        sub2 = args[2] if len(args) > 2 else ""
        if cmd == "plugin" and sub == "marketplace" and sub2 == "list":
            return _make_completed(stdout="")  # not registered
        if cmd == "plugin" and sub == "marketplace" and sub2 == "add":
            return _make_completed(stdout="registered\n")
        if cmd == "plugin" and sub == "list":
            return _make_completed(stdout="")
        if cmd == "mcp" and sub == "list":
            return _make_completed(stdout="")
        if cmd == "plugin" and sub == "install":
            return _make_completed(stdout="installed\n")
        if cmd == "mcp" and sub == "add":
            return _make_completed(stdout="added\n")
        return _make_completed(stdout="")

    with patch("dotfiles.claude_plugins.shutil.which", return_value="/usr/bin/claude"), \
         patch("dotfiles.claude_plugins._run_claude", side_effect=fake_run) as mock_run:
        run_claude_setup(RESOURCES, groups=["default"])

    add_calls = [
        c.args[0] for c in mock_run.call_args_list
        if c.args[0][:3] == ["plugin", "marketplace", "add"]
    ]
    assert len(add_calls) == 1
    assert "anthropics/life-sciences" in add_calls[0]


def test_marketplace_skipped_if_registered():
    """If life-sciences marketplace is already registered, don't re-register."""
    def fake_run(args, timeout=30):
        cmd, sub = args[0], args[1] if len(args) > 1 else ""
        sub2 = args[2] if len(args) > 2 else ""
        if cmd == "plugin" and sub == "marketplace" and sub2 == "list":
            return _make_completed(stdout="life-sciences\n")  # already registered
        if cmd == "plugin" and sub == "list":
            return _make_completed(stdout="")
        if cmd == "mcp" and sub == "list":
            return _make_completed(stdout="")
        if cmd == "plugin" and sub == "install":
            return _make_completed(stdout="installed\n")
        if cmd == "mcp" and sub == "add":
            return _make_completed(stdout="added\n")
        return _make_completed(stdout="")

    with patch("dotfiles.claude_plugins.shutil.which", return_value="/usr/bin/claude"), \
         patch("dotfiles.claude_plugins._run_claude", side_effect=fake_run) as mock_run:
        run_claude_setup(RESOURCES, groups=["default"])

    add_calls = [
        c.args[0] for c in mock_run.call_args_list
        if c.args[0][:3] == ["plugin", "marketplace", "add"]
    ]
    assert add_calls == [], "Should not re-register an already-registered marketplace"


# ── run_claude_setup — unknown group ─────────────────────────────────────────

def test_setup_handles_unknown_group_gracefully(capsys):
    with patch("dotfiles.claude_plugins.shutil.which", return_value="/usr/bin/claude"), \
         patch("dotfiles.claude_plugins._run_claude",
               return_value=_make_completed(stdout="")):
        result = run_claude_setup(RESOURCES, groups=["nonexistent-group"])
    # Should return without crashing; may return empty list
    assert isinstance(result, list)
    captured = capsys.readouterr()
    assert "unknown plugin group" in captured.err


# ── run_claude_setup — mcp-stdio binary check ────────────────────────────────

def test_mcp_stdio_skipped_when_binary_missing(capsys):
    """mcp-stdio integrations whose command is not on PATH should report a
    useful error rather than attempting to run claude mcp add."""

    def fake_run(args, timeout=30):
        cmd, sub = args[0], args[1] if len(args) > 1 else ""
        sub2 = args[2] if len(args) > 2 else ""
        if cmd == "plugin" and sub == "marketplace" and sub2 == "list":
            return _make_completed(stdout="life-sciences\n")
        if cmd == "plugin" and sub == "list":
            return _make_completed(stdout="")
        if cmd == "mcp" and sub == "list":
            return _make_completed(stdout="")
        if cmd == "plugin" and sub == "install":
            return _make_completed(stdout="installed\n")
        return _make_completed(stdout="")

    def fake_which(cmd):
        if cmd == "claude":
            return "/usr/bin/claude"
        return None   # all other commands (tooluniverse) not on PATH

    with patch("dotfiles.claude_plugins.shutil.which", side_effect=fake_which), \
         patch("dotfiles.claude_plugins._run_claude", side_effect=fake_run) as mock_run:
        statuses = run_claude_setup(RESOURCES, groups=["bioinformatics"])

    tooluniverse = next((s for s in statuses if s.name == "tooluniverse"), None)
    assert tooluniverse is not None
    assert not tooluniverse.installed
    assert "command not found" in tooluniverse.message

    mcp_add_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][:2] == ["mcp", "add"]
    ]
    assert mcp_add_calls == [], "Should not call mcp add when binary is missing"


# ── Secrets never appear in output ───────────────────────────────────────────

_SECRET_VALUES = [
    "sk-ant-secret-test",
    "ghs_fake_token",
    "AKIAFAKEKEYDONOTUSE",
    "synapse_fake_token",
]


@pytest.mark.parametrize("secret", _SECRET_VALUES)
def test_no_secrets_in_setup_output(secret, capsys):
    """Credential values must never appear in setup output."""
    env_override = {
        "ANTHROPIC_API_KEY": secret,
        "GH_TOKEN": secret,
        "SYNAPSE_AUTH_TOKEN": secret,
    }

    def fake_run(args, timeout=30):
        cmd, sub = args[0], args[1] if len(args) > 1 else ""
        sub2 = args[2] if len(args) > 2 else ""
        if cmd == "plugin" and sub == "marketplace" and sub2 == "list":
            return _make_completed(stdout="life-sciences\n")
        if cmd == "plugin" and sub == "list":
            return _make_completed(stdout="")
        if cmd == "mcp" and sub == "list":
            return _make_completed(stdout="")
        if cmd == "plugin" and sub == "install":
            return _make_completed(stdout="ok\n")
        if cmd == "mcp" and sub == "add":
            return _make_completed(stdout="ok\n")
        return _make_completed(stdout="")

    with patch.dict(os.environ, env_override, clear=False), \
         patch("dotfiles.claude_plugins.shutil.which", return_value="/usr/bin/claude"), \
         patch("dotfiles.claude_plugins._run_claude", side_effect=fake_run):
        run_claude_setup(RESOURCES, groups=["default"])

    captured = capsys.readouterr()
    all_output = captured.out + captured.err
    assert secret not in all_output, f"Secret appeared in output: {secret!r}"


# ── check_plugin_statuses (read-only, used by doctor) ─────────────────────────

def test_check_statuses_returns_empty_when_claude_missing():
    with patch("dotfiles.claude_plugins.shutil.which", return_value=None):
        result = check_plugin_statuses(RESOURCES)
    assert result == []


def test_check_statuses_reports_installed():
    plugin_list = (
        "github@claude-plugins-official\n"
        "context7\n"
    )
    mcp_list = "context7\n"

    def fake_run(args, timeout=30):
        if args[:2] == ["plugin", "list"]:
            return _make_completed(stdout=plugin_list)
        if args[:2] == ["mcp", "list"]:
            return _make_completed(stdout=mcp_list)
        return _make_completed(stdout="")

    with patch("dotfiles.claude_plugins.shutil.which", return_value="/usr/bin/claude"), \
         patch("dotfiles.claude_plugins._run_claude", side_effect=fake_run):
        statuses = check_plugin_statuses(RESOURCES, groups=["default"])

    github = next((s for s in statuses if s.name == "github"), None)
    assert github is not None
    assert github.installed is True

    context7 = next((s for s in statuses if s.name == "context7"), None)
    assert context7 is not None
    assert context7.installed is True


def test_check_statuses_reports_not_installed():
    def fake_run(args, timeout=30):
        return _make_completed(stdout="")  # nothing installed

    with patch("dotfiles.claude_plugins.shutil.which", return_value="/usr/bin/claude"), \
         patch("dotfiles.claude_plugins._run_claude", side_effect=fake_run):
        statuses = check_plugin_statuses(RESOURCES, groups=["default"])

    for s in statuses:
        assert not s.installed
