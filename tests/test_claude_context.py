"""Tests for shared Claude and Codex context budget invariants.

These tests enforce structural properties, not exact prose.  They are
intentionally tolerant of wording changes but strict about:

- token budgets
- content isolation (no environment-specific text leaking into global)
- composition correctness
"""
from __future__ import annotations

import json

import pytest

import tomllib

from .conftest import (
    REPO_ROOT,
    apply_chezmoi,
    chezmoi_status,
    render,
    requires_chezmoi,
)

# ── context budget contract ───────────────────────────────────────────────────
# Agent instructions are loaded into every session, so their size is a hard
# invariant rather than a report. These budgets are documented in
# docs/agent-context.md; this module is the only thing that enforces them.
GLOBAL_BUDGET = 900
OVERLAY_BUDGET = 500


def estimate_tokens(text: str) -> int:
    """Words x 4/3, rounded down -- a standard BPE approximation for prose."""
    return len(text.split()) * 4 // 3


# ── helpers ───────────────────────────────────────────────────────────────────

# Instruction fragments are chezmoi templates, composed into ~/.claude/CLAUDE.md
# and ~/.codex/AGENTS.md at apply time. They live under .chezmoitemplates/
# precisely so chezmoi never installs them as targets of their own.
SOURCE = REPO_ROOT / "home"
TEMPLATES = SOURCE / ".chezmoitemplates"

SHARED_MD = TEMPLATES / "agents-preferences.md"
CLAUDE_MD = TEMPLATES / "claude-instructions.md"
CODEX_MD = TEMPLATES / "codex-instructions.md"
CODEX_SETTINGS = TEMPLATES / "codex-preferences.toml"
CODEOCEAN_MD = TEMPLATES / "codeocean-preferences.md"
GLOBAL_GITIGNORE = SOURCE / "dot_gitignore"
CODEOCEAN_EXPORTS = SOURCE / "dot_exports.codeocean"
CLAUDE_SETTINGS = SOURCE / "dot_claude" / "settings.json"
CODEOCEAN_GLOBAL = SOURCE / "modify_private_dot_claude.json"


def _global_text() -> str:
    return SHARED_MD.read_text()


def _codeocean_text() -> str:
    return CODEOCEAN_MD.read_text()


def test_repository_agent_instructions_stay_aligned():
    assert (REPO_ROOT / "AGENTS.md").read_text() == (REPO_ROOT / "CLAUDE.md").read_text()


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


@requires_chezmoi
def test_codeocean_global_defaults_only_skip_onboarding(tmp_path):
    """~/.claude.json gains exactly one managed key and nothing else."""
    result = apply_chezmoi(tmp_path, "codeocean")
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / ".claude.json").read_text()) == {
        "hasCompletedOnboarding": True,
    }


@requires_chezmoi
def test_codeocean_global_merge_preserves_app_state(tmp_path):
    """The managed key is merged into app-written state, not written over it."""
    (tmp_path / ".claude.json").write_text(
        json.dumps({"userID": "abc123", "hasCompletedOnboarding": False})
    )
    result = apply_chezmoi(tmp_path, "codeocean")
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / ".claude.json").read_text()) == {
        "userID": "abc123",
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


def test_shared_project_memory_uses_singular_agent_directory():
    """Both agents share one ignored project-local memory directory."""
    text = _global_text() + (REPO_ROOT / "docs" / "agent-context.md").read_text()
    assert ".agents/memory/" in text
    assert ".agents/memory/" in GLOBAL_GITIGNORE.read_text()
    assert ".agents/memory/" in (REPO_ROOT / ".gitignore").read_text()
    for obsolete in (".claude/memory/", ".codex/memories/", ".agents/memories/"):
        assert obsolete not in text
        assert obsolete not in GLOBAL_GITIGNORE.read_text()
    assert "memories = true" not in CODEX_SETTINGS.read_text()


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

@requires_chezmoi
@pytest.mark.parametrize(
    ("template", "agent_heading"),
    [
        ("dot_claude/CLAUDE.md.tmpl", "Claude delegation"),
        ("dot_codex/AGENTS.md.tmpl", "Codex delegation"),
    ],
)
def test_codeocean_effective_context_contains_shared_and_specific_layers(
    template, agent_heading
):
    """Both agents receive shared, agent-specific, and Code Ocean guidance."""
    content = render(template, "codeocean")
    assert "Working style" in content
    assert agent_heading in content
    assert "Code Ocean" in content
    assert "/scratch" in content


@requires_chezmoi
@pytest.mark.parametrize(
    "template", ["dot_claude/CLAUDE.md.tmpl", "dot_codex/AGENTS.md.tmpl"]
)
def test_non_overlay_profile_omits_codeocean_layer(template):
    """A profile without the codeocean layer gets only the shared base."""
    content = render(template, "linux")
    assert "Working style" in content
    assert "Code Ocean" not in content


@requires_chezmoi
@pytest.mark.parametrize(
    "target", [".claude/CLAUDE.md", ".codex/AGENTS.md"]
)
def test_agent_instructions_are_generated_files_and_idempotent(tmp_path, target):
    """Composed instructions are regular files, and re-applying does not churn."""
    assert apply_chezmoi(tmp_path, "codeocean").returncode == 0
    generated = tmp_path / target
    assert generated.is_file() and not generated.is_symlink()
    first = generated.read_text()
    first_mtime = generated.stat().st_mtime_ns

    assert apply_chezmoi(tmp_path, "codeocean").returncode == 0
    assert generated.read_text() == first
    assert generated.stat().st_mtime_ns == first_mtime
    assert chezmoi_status(tmp_path) == ""


# ── idempotency test ─────────────────────────────────────────────────────────
