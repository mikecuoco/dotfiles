"""Tests for authentication checks."""
import os
from unittest.mock import patch, MagicMock

import pytest

from dotfiles.auth import (
    check_anthropic,
    check_openai,
    check_github,
    check_synapse,
    check_codeocean,
    check_aws,
    check_mem0,
    all_statuses,
    run_auth,
)


# ── Anthropic ─────────────────────────────────────────────────────────────────

def test_anthropic_configured():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-abc123"}, clear=True):
        s = check_anthropic()
    assert s.configured is True
    assert "sk-test-abc123" not in s.message  # secret must not appear in output


def test_anthropic_not_configured():
    with patch.dict(os.environ, {}, clear=True), \
         patch("dotfiles.auth.shutil.which", return_value=None):
        s = check_anthropic()
    assert s.configured is False
    assert s.required is True


def test_anthropic_subscription_oauth_uses_canonical_name():
    with patch.dict(
        os.environ,
        {"CLAUDE_CODE_OAUTH_TOKEN": "oauth-secret"},
        clear=True,
    ):
        s = check_anthropic()
    assert s.configured is True
    assert "CLAUDE_CODE_OAUTH_TOKEN" in s.message
    assert "subscription OAuth" in s.message
    assert "oauth-secret" not in s.message


def test_anthropic_custom_bearer_is_not_described_as_oauth():
    with patch.dict(
        os.environ,
        {"ANTHROPIC_AUTH_TOKEN": "gateway-secret"},
        clear=True,
    ):
        s = check_anthropic()
    assert s.configured is True
    assert "custom bearer" in s.message
    assert "OAuth" not in s.message


def test_anthropic_reports_api_key_oauth_conflict():
    with patch.dict(
        os.environ,
        {
            "ANTHROPIC_API_KEY": "api-secret",
            "CLAUDE_CODE_OAUTH_TOKEN": "oauth-secret",
        },
        clear=True,
    ):
        s = check_anthropic()
    assert s.configured is True
    assert "both set" in s.message
    assert "api-secret" not in s.message
    assert "oauth-secret" not in s.message


# ── GitHub ────────────────────────────────────────────────────────────────────

def test_github_gh_token():
    with patch.dict(os.environ, {"GH_TOKEN": "ghs_fake"}, clear=False):
        s = check_github()
    assert s.configured is True
    assert "ghs_fake" not in s.message


def test_github_cli_logged_in():
    import shutil
    env = {k: v for k, v in os.environ.items()
           if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
    with patch.dict(os.environ, env, clear=True), \
         patch("dotfiles.auth.shutil.which", return_value="/usr/bin/gh"), \
         patch("dotfiles.auth.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Logged in to github.com\n")
        s = check_github()
    assert s.configured is True


def test_github_not_configured():
    env = {k: v for k, v in os.environ.items()
           if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
    with patch.dict(os.environ, env, clear=True), \
         patch("dotfiles.auth.shutil.which", return_value=None):
        s = check_github()
    assert s.configured is False


# ── Synapse and Code Ocean ───────────────────────────────────────────────────

def test_synapse_uses_canonical_token_name():
    with patch.dict(os.environ, {"SYNAPSE_AUTH_TOKEN": "synapse-secret"}, clear=True):
        s = check_synapse()
    assert s.configured is True
    assert s.required is False
    assert "SYNAPSE_AUTH_TOKEN" in s.message
    assert "synapse-secret" not in s.message


def test_codeocean_requires_canonical_token_and_domain():
    with patch.dict(
        os.environ,
        {
            "CODEOCEAN_API_TOKEN": "codeocean-secret",
            "CODEOCEAN_DOMAIN": "https://codeocean.example.org",
        },
        clear=True,
    ):
        s = check_codeocean()
    assert s.configured is True
    assert s.required is False
    assert "CODEOCEAN_API_TOKEN" in s.message
    assert "CODEOCEAN_DOMAIN" in s.message
    assert "codeocean-secret" not in s.message
    assert "codeocean.example.org" not in s.message


def test_codeocean_reports_missing_domain_without_leaking_token():
    with patch.dict(
        os.environ,
        {"CODEOCEAN_API_TOKEN": "codeocean-secret"},
        clear=True,
    ):
        s = check_codeocean()
    assert s.configured is False
    assert "CODEOCEAN_DOMAIN" in s.message
    assert "codeocean-secret" not in s.message


# ── AWS ───────────────────────────────────────────────────────────────────────

def test_aws_env_vars_set_and_cli_validates():
    with patch.dict(os.environ, {
        "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
        "AWS_SECRET_ACCESS_KEY": "secret",
    }, clear=False), \
    patch("dotfiles.auth.shutil.which", return_value="/usr/bin/aws"), \
    patch("dotfiles.auth.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="123456789012\n")
        s = check_aws()
    assert s.configured is True
    assert "AKIAIOSFODNN7EXAMPLE" not in s.message  # key must not appear in output
    assert "secret" not in s.message


def test_aws_not_required():
    s = check_aws()
    assert s.required is False


def test_openai_configured():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai-fake"}, clear=False):
        s = check_openai()
    assert s.configured is True
    assert "sk-openai-fake" not in s.message  # secret must not appear


def test_openai_not_configured():
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        s = check_openai()
    assert s.configured is False
    assert s.required is False  # optional


def test_mem0_optional():
    s = check_mem0()
    assert s.required is False


# ── Secrets never appear in output ───────────────────────────────────────────

SECRET_VALUES = ["sk-ant-abc123", "ghs_fake_token", "AKIAIOSFODNN7EXAMPLE",
                 "super_secret_key", "mem0_secret_key", "sk-openai-abc123"]


@pytest.mark.parametrize("secret", SECRET_VALUES)
def test_secrets_not_in_auth_output(secret, capsys):
    env_override = {
        "ANTHROPIC_API_KEY": secret,
        "ANTHROPIC_AUTH_TOKEN": secret,
        "CLAUDE_CODE_OAUTH_TOKEN": secret,
        "OPENAI_API_KEY": secret,
        "GH_TOKEN": secret,
        "SYNAPSE_AUTH_TOKEN": secret,
        "CODEOCEAN_API_TOKEN": secret,
        "AWS_ACCESS_KEY_ID": secret,
        "AWS_SECRET_ACCESS_KEY": secret,
        "AWS_SESSION_TOKEN": secret,
        "MEM0_API_KEY": secret,
    }
    with patch.dict(os.environ, env_override, clear=False), \
         patch("dotfiles.auth.shutil.which", return_value=None):
        run_auth()
    captured = capsys.readouterr()
    assert secret not in captured.out, f"Secret '{secret}' appeared in stdout"
    assert secret not in captured.err, f"Secret '{secret}' appeared in stderr"
