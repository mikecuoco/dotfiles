"""Tests for shared Claude and Codex context budget invariants.

These tests enforce structural properties, not exact prose.  They are
intentionally tolerant of wording changes but strict about:

- token budgets
- content isolation (no environment-specific text leaking into global)
- composition correctness
- estimation determinism
"""
from __future__ import annotations

import json

import pytest

from dotfiles import RESOURCES_DIR
from dotfiles._toml import tomllib
from dotfiles.claude_stats import estimate_tokens, GLOBAL_BUDGET, OVERLAY_BUDGET

# ── helpers ───────────────────────────────────────────────────────────────────

SHARED_MD = RESOURCES_DIR / "common" / "agents" / "PREFERENCES.md"
CLAUDE_MD = RESOURCES_DIR / "common" / "claude" / "CLAUDE.md"
CODEX_MD = RESOURCES_DIR / "common" / "codex" / "AGENTS.md"
CODEX_SETTINGS = RESOURCES_DIR / "common" / "codex" / "preferences.toml"
GLOBAL_GITIGNORE = RESOURCES_DIR / "common" / "git" / ".gitignore"
CODEOCEAN_MD = RESOURCES_DIR / "codeocean" / "agents" / "PREFERENCES.md"
CODEOCEAN_EXPORTS = RESOURCES_DIR / "codeocean" / "shell" / ".exports.codeocean"
CLAUDE_SETTINGS = RESOURCES_DIR / "common" / "claude" / "settings.json"
CODEOCEAN_GLOBAL = RESOURCES_DIR / "codeocean" / "claude" / "global.json"


def _global_text() -> str:
    return SHARED_MD.read_text()


def _codeocean_text() -> str:
    return CODEOCEAN_MD.read_text()


# ── budget tests ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("supplement", [CLAUDE_MD, CODEX_MD])
def test_global_agent_instructions_within_budget(supplement):
    """Each generated global instruction file must stay within budget."""
    text = _global_text() + "\n\n" + supplement.read_text()
    tokens = estimate_tokens(text)
    assert tokens <= GLOBAL_BUDGET, (
        f"Global instructions are {tokens} estimated tokens "
        f"(budget: {GLOBAL_BUDGET}). Trim them or raise the budget intentionally."
    )


def test_codeocean_overlay_within_budget():
    """Code Ocean overlay must stay within the overlay token budget."""
    tokens = estimate_tokens(_codeocean_text())
    assert tokens <= OVERLAY_BUDGET, (
        f"Code Ocean agent overlay is {tokens} estimated tokens "
        f"(budget: {OVERLAY_BUDGET}). "
        "Trim it or raise the budget intentionally."
    )


def test_codeocean_runtime_storage_points_to_scratch():
    """Runtime temp, cache, environment, and installation roots stay off `/`."""
    text = CODEOCEAN_EXPORTS.read_text()
    required = (
        "TMPDIR",
        "TMP",
        "TEMP",
        "XDG_CACHE_HOME",
        "CONDA_PKGS_DIRS",
        "CONDA_ENVS_PATH",
        "MAMBA_ROOT_PREFIX",
        "PIP_CACHE_DIR",
        "PYTHONUSERBASE",
        "PYTHONPYCACHEPREFIX",
        "VIRTUALENV_OVERRIDE_APP_DATA",
        "PRE_COMMIT_HOME",
        "UV_CACHE_DIR",
        "UV_TOOL_DIR",
        "PIPX_HOME",
        "POETRY_VIRTUALENVS_PATH",
        "NPM_CONFIG_PREFIX",
        "PNPM_HOME",
        "BUN_INSTALL",
        "CARGO_HOME",
        "RUSTUP_HOME",
        "GOPATH",
        "GOBIN",
        "JULIA_DEPOT_PATH",
        "HF_HOME",
        "TORCH_HOME",
        "TORCH_EXTENSIONS_DIR",
        "CUDA_CACHE_PATH",
        "TRITON_CACHE_DIR",
        "JAX_COMPILATION_CACHE_DIR",
        "R_LIBS_USER",
    )
    assert "_dotfiles_scratch=\"/scratch/.dotfiles\"" in text
    for variable in required:
        assert f"export {variable}=" in text, f"{variable} is not redirected"


def test_codeocean_only_eagerly_creates_required_temp_directory():
    """Starting a shell creates only the nested temp directory tools require."""
    mkdir_lines = [
        line.strip()
        for line in CODEOCEAN_EXPORTS.read_text().splitlines()
        if line.strip().startswith("mkdir ")
    ]
    assert mkdir_lines == ['mkdir -p "$TMPDIR"']


def test_shared_claude_settings_are_minimal_and_secret_safe():
    settings = json.loads(CLAUDE_SETTINGS.read_text())

    assert settings["$schema"] == "https://json.schemastore.org/claude-code-settings.json"
    assert settings["cleanupPeriodDays"] == 30
    assert settings["respectGitignore"] is True
    assert settings["useAutoModeDuringPlan"] is True
    assert "includeCoAuthoredBy" not in settings
    assert "env" not in settings
    denied = set(settings["permissions"]["deny"])
    assert {
        "Read(./.env)",
        "Read(./secrets/**)",
        "Read(~/.extra)",
        "Read(~/.aws/credentials)",
        "Read(~/.claude/.credentials.json)",
    } <= denied


def test_shared_codex_settings_define_secret_safe_workspace_profile():
    settings = tomllib.loads(CODEX_SETTINGS.read_text())

    assert settings["default_permissions"] == "dotfiles"
    profile = settings["permissions"]["dotfiles"]
    assert profile["extends"] == ":workspace"
    filesystem = profile["filesystem"]
    workspace = filesystem[":workspace_roots"]
    assert {
        "**/.env",
        "**/.env.*",
        "**/secrets/**",
        "**/.codex/auth.json",
    } <= {path for path, access in workspace.items() if access == "deny"}
    assert filesystem["/Users/*/.aws/credentials"] == "deny"
    assert filesystem["/home/*/.aws/credentials"] == "deny"
    assert filesystem["/root/.aws/credentials"] == "deny"
    assert filesystem["/Users/*/.codex/auth.json"] == "deny"


def test_codeocean_global_defaults_only_skip_onboarding():
    assert json.loads(CODEOCEAN_GLOBAL.read_text()) == {
        "hasCompletedOnboarding": True,
    }


# ── content-isolation tests ───────────────────────────────────────────────────

def test_no_scratch_in_global():
    """/scratch is Code Ocean-specific and must not appear globally."""
    assert "/scratch" not in _global_text(), (
        "Shared preferences contain '/scratch', which is Code Ocean-specific. "
        "Move it to the codeocean overlay."
    )


def test_no_cfg_memory_path_in_global():
    """The brittle /cfg/projects harness path must not appear globally."""
    assert "/cfg/projects" not in _global_text(), (
        "Shared preferences reference '/cfg/projects', a platform-specific memory path. "
        "Replace with portable memory policy guidance."
    )


def test_global_memory_policy_uses_mirrored_local_agent_directories():
    """Conversation summaries are mirrored in both local agent stores."""
    text = _global_text()
    for directory in (".claude/memory/", ".codex/memories/"):
        assert directory in text
        assert directory in GLOBAL_GITIGNORE.read_text()
    assert "every completed conversation" in text
    assert "Markdown summary" in text
    assert "in sync" in text


def test_no_codeocean_text_in_global():
    """Code Ocean-specific content must not appear in shared preferences."""
    text = _global_text()
    assert "Code Ocean" not in text, (
        "Shared preferences contain 'Code Ocean' text. "
        "Move it to the codeocean overlay."
    )
    assert "codeocean" not in text.lower(), (
        "Shared preferences reference 'codeocean'. "
        "Move it to the codeocean overlay."
    )


# ── composition test ──────────────────────────────────────────────────────────

def test_codeocean_effective_context_contains_shared_and_specific_layers(tmp_path):
    """Both agents receive shared, agent-specific, and Code Ocean guidance."""
    from dotfiles.install import run_install

    ok = run_install(profile="codeocean", dry_run=False, home=tmp_path)
    assert ok is True

    expected = {
        tmp_path / ".claude" / "CLAUDE.md": "Claude delegation",
        tmp_path / ".codex" / "AGENTS.md": "Codex delegation",
    }
    for generated, agent_heading in expected.items():
        assert generated.exists()
        assert not generated.is_symlink()
        content = generated.read_text()
        assert "Working style" in content
        assert agent_heading in content
        assert "Code Ocean" in content
        assert "/scratch" in content


# ── determinism test ─────────────────────────────────────────────────────────

def test_estimate_tokens_deterministic():
    """Token estimation must be purely deterministic."""
    sample = "This is a sample agent instruction with some technical words."
    assert estimate_tokens(sample) == estimate_tokens(sample)
    assert estimate_tokens(sample) == estimate_tokens(sample)

    # Also verify the formula: words * 4 // 3
    words = len(sample.split())
    expected = words * 4 // 3
    assert estimate_tokens(sample) == expected


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_estimate_tokens_no_external_calls(monkeypatch):
    """estimate_tokens must not make any I/O or subprocess calls."""
    import subprocess
    original_run = subprocess.run

    called = []

    def mock_run(*args, **kwargs):
        called.append(args)
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)
    estimate_tokens("hello world test")
    assert not called, "estimate_tokens should not call subprocess.run"


# ── idempotency test ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("relative", [".claude/CLAUDE.md", ".codex/AGENTS.md"])
def test_codeocean_agent_instructions_idempotent(tmp_path, relative):
    """Re-installing Code Ocean does not rewrite generated instructions."""
    from dotfiles.install import run_install

    run_install(profile="codeocean", dry_run=False, home=tmp_path)
    generated = tmp_path / relative
    first = generated.read_text()
    first_mtime = generated.stat().st_mtime_ns

    run_install(profile="codeocean", dry_run=False, home=tmp_path)
    second = generated.read_text()

    assert first == second
    assert generated.stat().st_mtime_ns == first_mtime


def test_non_overlay_profile_generates_both_agent_instruction_files(tmp_path):
    """Common agent-specific supplements are composed for both tools."""
    from dotfiles.install import run_install

    run_install(profile="linux", dry_run=False, home=tmp_path)
    for relative in (".claude/CLAUDE.md", ".codex/AGENTS.md"):
        generated = tmp_path / relative
        assert generated.exists()
        assert not generated.is_symlink()


# ── agent-stats output test ──────────────────────────────────────────────────

def test_agent_stats_output_contains_no_secret_values(capsys):
    """The compatibility command must never print secret values."""
    import os
    from dotfiles.claude_stats import run_claude_stats

    fake_secrets = [
        "sk-ant-FAKESECRET123",
        "oauth-FAKESECRET123",
        "ghp_FAKEGITHUBTOKEN456",
        "synapse-fake-token",
        "codeocean-fake-token",
        "AKIAFAKEAWSKEY789",
        "fake-aws-session-token",
        "fake-mem0-key-abc",
        "fake-openai-key-xyz",
    ]
    env_patch = {
        "ANTHROPIC_API_KEY": fake_secrets[0],
        "CLAUDE_CODE_OAUTH_TOKEN": fake_secrets[1],
        "GH_TOKEN": fake_secrets[2],
        "SYNAPSE_AUTH_TOKEN": fake_secrets[3],
        "CODEOCEAN_API_TOKEN": fake_secrets[4],
        "AWS_ACCESS_KEY_ID": fake_secrets[5],
        "AWS_SESSION_TOKEN": fake_secrets[6],
        "MEM0_API_KEY": fake_secrets[7],
        "OPENAI_API_KEY": fake_secrets[8],
    }
    original = {k: os.environ.get(k) for k in env_patch}
    try:
        os.environ.update(env_patch)
        run_claude_stats()
        captured = capsys.readouterr()
        output = captured.out + captured.err
        for secret in fake_secrets:
            assert secret not in output, f"Secret value '{secret}' leaked into claude-stats output"
    finally:
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
