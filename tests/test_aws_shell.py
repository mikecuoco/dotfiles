"""Tests for the AWS SSO shell helpers."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


FUNCTIONS = (
    Path(__file__).parents[1]
    / "src"
    / "dotfiles"
    / "resources"
    / "common"
    / "shell"
    / ".functions"
)


def _fake_aws(tmp_path: Path) -> tuple[Path, Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    auth_file = tmp_path / "authenticated"
    log_file = tmp_path / "aws.log"
    aws = bin_dir / "aws"
    aws.write_text(
        """#!/usr/bin/env bash
case "$1 $2" in
    "configure get")
        case "$5" in
            storage) printf 'StorageWorkgroupRW\\n' ;;
            sensitive) printf 'HighlySensitiveSEAADStorageRW\\n' ;;
        esac
        ;;
    "configure list-profiles")
        printf 'storage\\nsensitive\\n'
        ;;
    "sts get-caller-identity")
        [ -f "$AWS_STUB_AUTH" ] || exit 255
        printf '123456789012\\tarn:aws:sts::123456789012:assumed-role/Test/user\\n'
        ;;
    "sso login")
        printf '%s\\n' "$*" > "$AWS_STUB_LOG"
        touch "$AWS_STUB_AUTH"
        ;;
    *)
        exit 2
        ;;
esac
"""
    )
    aws.chmod(0o755)
    return bin_dir, auth_file, log_file


def test_sensitive_logs_in_and_selects_profile(tmp_path: Path) -> None:
    bin_dir, auth_file, log_file = _fake_aws(tmp_path)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "AWS_STUB_AUTH": str(auth_file),
        "AWS_STUB_LOG": str(log_file),
        "AWS_ACCESS_KEY_ID": "old-access-key",
        "AWS_SECRET_ACCESS_KEY": "old-secret-key",
        "AWS_SESSION_TOKEN": "old-session-token",
    }
    script = """
source "$1"
aws-sensitive
printf 'PROFILE=%s\\n' "$AWS_PROFILE"
printf 'ACCESS_KEY=%s\\n' "${AWS_ACCESS_KEY_ID-unset}"
"""

    result = subprocess.run(
        ["bash", "-c", script, "--", str(FUNCTIONS)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "PROFILE=sensitive" in result.stdout
    assert "ACCESS_KEY=unset" in result.stdout
    assert log_file.read_text().strip() == "sso login --profile sensitive"


def test_storage_reuses_valid_session(tmp_path: Path) -> None:
    bin_dir, auth_file, log_file = _fake_aws(tmp_path)
    auth_file.touch()
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "AWS_STUB_AUTH": str(auth_file),
        "AWS_STUB_LOG": str(log_file),
    }

    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; aws-storage; printf "PROFILE=%s\\n" "$AWS_PROFILE"',
            "--",
            str(FUNCTIONS),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "PROFILE=storage" in result.stdout
    assert not log_file.exists()
