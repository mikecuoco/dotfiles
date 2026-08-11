"""Authentication health checks — checks presence, never prints values."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class AuthStatus:
    name: str
    configured: bool
    message: str
    required: bool = True


# ── Individual checks ─────────────────────────────────────────────────────────

def check_anthropic() -> AuthStatus:
    """Check Claude Code auth: API key, subscription OAuth, bearer token, or login."""
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_oauth = bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"))
    if has_api_key and has_oauth:
        return AuthStatus(
            "Anthropic / Claude",
            True,
            "ANTHROPIC_API_KEY and CLAUDE_CODE_OAUTH_TOKEN are both set; "
            "the API key can override subscription OAuth",
        )
    if has_api_key:
        return AuthStatus("Anthropic / Claude", True, "ANTHROPIC_API_KEY is set")
    if has_oauth:
        return AuthStatus(
            "Anthropic / Claude",
            True,
            "CLAUDE_CODE_OAUTH_TOKEN is set (subscription OAuth)",
        )
    if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return AuthStatus(
            "Anthropic / Claude",
            True,
            "ANTHROPIC_AUTH_TOKEN is set (custom bearer credential)",
        )
    # claude.ai login via CLI (per-machine OAuth session)
    if shutil.which("claude"):
        try:
            result = subprocess.run(
                ["claude", "auth", "status", "--json"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                if data.get("loggedIn"):
                    method = data.get("authMethod", "unknown")
                    org = data.get("orgName", "")
                    detail = f"{method} ({org})" if org else method
                    return AuthStatus("Anthropic / Claude", True, f"claude auth: {detail}")
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass
    return AuthStatus(
        "Anthropic / Claude", False,
        "No Claude auth found — run: claude auth login, or set "
        "CLAUDE_CODE_OAUTH_TOKEN for an ephemeral environment",
    )


def check_github() -> AuthStatus:
    """Check GitHub auth via GH_TOKEN env var or gh CLI."""
    if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
        return AuthStatus("GitHub", True, "GH_TOKEN is set")

    if shutil.which("gh"):
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                # Extract the first meaningful line from gh auth status
                first = next(
                    (ln.strip() for ln in result.stdout.splitlines() if ln.strip()),
                    "logged in",
                )
                return AuthStatus("GitHub", True, f"gh: {first}")
            return AuthStatus(
                "GitHub", False,
                f"gh auth status failed — run: gh auth login",
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

    return AuthStatus(
        "GitHub", False,
        "GH_TOKEN not set and gh CLI not found — install gh or set GH_TOKEN",
    )


def check_synapse() -> AuthStatus:
    """Check the canonical Synapse personal-access-token variable."""
    if os.environ.get("SYNAPSE_AUTH_TOKEN"):
        return AuthStatus(
            "Synapse",
            True,
            "SYNAPSE_AUTH_TOKEN is set",
            required=False,
        )
    return AuthStatus(
        "Synapse",
        False,
        "SYNAPSE_AUTH_TOKEN not set (optional — skip if not using Synapse)",
        required=False,
    )


def check_codeocean() -> AuthStatus:
    """Check the canonical Code Ocean API token and non-secret domain."""
    has_token = bool(os.environ.get("CODEOCEAN_API_TOKEN"))
    has_domain = bool(os.environ.get("CODEOCEAN_DOMAIN"))
    if has_token and has_domain:
        return AuthStatus(
            "Code Ocean API",
            True,
            "CODEOCEAN_API_TOKEN and CODEOCEAN_DOMAIN are set",
            required=False,
        )
    missing = []
    if not has_token:
        missing.append("CODEOCEAN_API_TOKEN")
    if not has_domain:
        missing.append("CODEOCEAN_DOMAIN")
    return AuthStatus(
        "Code Ocean API",
        False,
        f"{', '.join(missing)} not set (optional — required for API enrichment)",
        required=False,
    )


def check_aws() -> AuthStatus:
    """Check AWS credentials via env vars, credentials file, or aws CLI."""
    has_key = bool(os.environ.get("AWS_ACCESS_KEY_ID"))
    has_secret = bool(os.environ.get("AWS_SECRET_ACCESS_KEY"))
    has_profile = bool(
        os.environ.get("AWS_PROFILE") or os.environ.get("AWS_DEFAULT_PROFILE")
    )
    creds_file = os.path.expanduser("~/.aws/credentials")

    env_source = (
        "AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY" if (has_key and has_secret)
        else "AWS_PROFILE" if has_profile
        else None
    )

    if shutil.which("aws"):
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity",
                 "--output", "text", "--query", "Account"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                acct = result.stdout.strip()
                src = f" via {env_source}" if env_source else ""
                return AuthStatus(
                    "AWS", True,
                    f"AWS account {acct}{src}",
                    required=False,
                )
            sso_session = _find_sso_session()
            if sso_session:
                return AuthStatus(
                    "AWS", False,
                    f"SSO configured but not logged in — run: aws sso login --sso-session {sso_session}",
                    required=False,
                )
            hint = result.stderr.strip()[:120] if result.stderr else "no credentials"
            return AuthStatus(
                "AWS", False,
                f"aws sts get-caller-identity failed: {hint}",
                required=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

    if env_source:
        return AuthStatus(
            "AWS", True,
            f"{env_source} set (not validated — aws CLI not found)",
            required=False,
        )
    if os.path.exists(creds_file):
        return AuthStatus(
            "AWS", True,
            "~/.aws/credentials exists (not validated — aws CLI not found)",
            required=False,
        )
    return AuthStatus(
        "AWS", False,
        "No AWS credentials found (optional)",
        required=False,
    )


def _find_sso_session() -> str | None:
    """Return the first sso-session name found in ~/.aws/config, or None."""
    import configparser
    from pathlib import Path

    cfg = Path(os.path.expanduser("~/.aws/config"))
    if not cfg.exists():
        return None
    parser = configparser.ConfigParser()
    try:
        parser.read(cfg)
    except configparser.Error:
        return None
    for section in parser.sections():
        if section.startswith("sso-session "):
            return section.split(" ", 1)[1].strip()
    return None


def check_openai() -> AuthStatus:
    """Check OPENAI_API_KEY is set (used by Codex and ChatGPT API)."""
    if os.environ.get("OPENAI_API_KEY"):
        return AuthStatus("OpenAI / Codex", True, "OPENAI_API_KEY is set", required=False)
    return AuthStatus(
        "OpenAI / Codex", False,
        "OPENAI_API_KEY not set (optional — skip if not using Codex/ChatGPT API)",
        required=False,
    )


def check_mem0() -> AuthStatus:
    """Check MEM0_API_KEY is set (optional service)."""
    if os.environ.get("MEM0_API_KEY"):
        return AuthStatus("Mem0", True, "MEM0_API_KEY is set", required=False)
    return AuthStatus(
        "Mem0", False,
        "MEM0_API_KEY not set (optional — skip if not using Mem0)",
        required=False,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def all_statuses() -> list[AuthStatus]:
    return [
        check_anthropic(),
        check_openai(),
        check_github(),
        check_synapse(),
        check_codeocean(),
        check_aws(),
        check_mem0(),
    ]


def run_auth() -> int:
    """Print authentication status.  Returns non-zero if a required service is missing."""
    statuses = all_statuses()
    missing_required = False

    print("Authentication\n" + "─" * 40)
    for s in statuses:
        icon = "✓" if s.configured else ("✗" if s.required else "–")
        opt = "" if s.required else " (optional)"
        print(f"  {icon} {s.name}{opt}")
        print(f"      {s.message}")
        if s.required and not s.configured:
            missing_required = True

    if missing_required:
        print("\nSome required credentials are missing.")
        return 1
    return 0
