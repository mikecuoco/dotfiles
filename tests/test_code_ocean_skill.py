"""Tests for the first-party Code Ocean Claude Code skill."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from dotfiles.install import get_resources_dir


SKILL = (
    get_resources_dir()
    / "common"
    / "agents"
    / "skills"
    / "code-ocean-capsule"
)
CHECKER = SKILL / "scripts" / "check_capsule.py"
REFRESHER = SKILL / "scripts" / "refresh_datasets.py"


def _load_refresher(monkeypatch):
    """Load pure refresh logic without making ruamel.yaml a project dependency."""

    class CommentedMap(dict):
        pass

    class YAML:
        pass

    ruamel = types.ModuleType("ruamel")
    yaml_module = types.ModuleType("ruamel.yaml")
    comments_module = types.ModuleType("ruamel.yaml.comments")
    yaml_module.YAML = YAML
    comments_module.CommentedMap = CommentedMap
    monkeypatch.setitem(sys.modules, "ruamel", ruamel)
    monkeypatch.setitem(sys.modules, "ruamel.yaml", yaml_module)
    monkeypatch.setitem(sys.modules, "ruamel.yaml.comments", comments_module)
    monkeypatch.setattr(sys, "dont_write_bytecode", True)

    name = "_test_refresh_datasets"
    spec = importlib.util.spec_from_file_location(name, REFRESHER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def test_skill_local_links_resolve():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for relative in (
        "references/capsule-layout.md",
        "references/datasets.md",
        "references/environments.md",
        "references/reproducibility.md",
    ):
        assert f"]({relative})" in text
        assert (SKILL / relative).is_file()


def test_checker_treats_missing_final_artifacts_as_exploratory_info(tmp_path):
    arm = tmp_path / "code" / "01_preprocessing"
    arm.mkdir(parents=True)
    (arm / "01_explore.ipynb").write_text("{}", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(tmp_path), "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["stage"] == "exploration"
    assert report["counts"]["error"] == 0
    assert any(item["code"] == "missing-run" and item["severity"] == "info" for item in report["findings"])


def test_checker_enforces_finalization_requirements(tmp_path):
    arm = tmp_path / "code" / "preprocessing"
    arm.mkdir(parents=True)
    (arm / "analysis.py").write_text("pass\n", encoding="utf-8")
    metadata = tmp_path / ".codeocean"
    metadata.mkdir()
    (metadata / "datasets.json").write_text(
        '[{"id":"01234567-89ab-cdef-0123-456789abcdef","mount":"input"}]\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(tmp_path),
            "--stage",
            "finalization",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    codes = {item["code"] for item in report["findings"] if item["severity"] == "error"}
    assert {
        "unnumbered-analysis-arm",
        "missing-dataset-manifest",
        "missing-environment-spec",
        "missing-run",
    } <= codes
    assert any(
        item["code"] == "missing-conda-lock" and item["severity"] == "info"
        for item in report["findings"]
    )


def test_attachment_parser_accepts_list_and_uuid_mapping(monkeypatch):
    module = _load_refresher(monkeypatch)
    first = "01234567-89ab-cdef-0123-456789abcdef"
    second = "11111111-2222-3333-4444-555555555555"
    attachments = module.extract_attachments(
        {
            "datasets": [{"data_asset_id": first, "mount": "rna", "name": "RNA"}],
            second: {"mount_path": "/data/pathology"},
        }
    )

    by_id = {item.asset_id: item for item in attachments}
    assert by_id[first].mount == "/data/rna"
    assert by_id[first].name == "RNA"
    assert by_id[second].mount == "/data/pathology"


def test_manifest_merge_preserves_manual_fields_and_marks_detached(monkeypatch):
    module = _load_refresher(monkeypatch)
    attached_id = "01234567-89ab-cdef-0123-456789abcdef"
    detached_id = "11111111-2222-3333-4444-555555555555"
    document = {
        "datasets": {
            "rna": {
                "description": "Curated description",
                "notes": "Keep this",
                "codeocean": {"id": attached_id, "name": "Old name"},
                "aws": {"uri": "s3://canonical/rna/", "provenance": "manual"},
            },
            "old_asset": {"codeocean": {"id": detached_id}, "status": "attached"},
        }
    }
    metadata = {
        attached_id: {
            "name": "Current name",
            "type": "dataset",
            "state": "ready",
            "description": "API description",
            "source_bucket": {
                "origin": "aws",
                "bucket": "observed",
                "prefix": "rna",
            },
        }
    }

    merged, warnings = module.merge_manifest(
        document,
        [module.Attachment(attached_id, "/data/rna", "RNA")],
        metadata,
    )

    rna = merged["datasets"]["rna"]
    assert rna["description"] == "Curated description"
    assert rna["notes"] == "Keep this"
    assert rna["mount"] == "/data/rna"
    assert rna["status"] == "attached"
    assert rna["codeocean"]["name"] == "Current name"
    assert rna["aws"]["uri"] == "s3://canonical/rna/"
    assert rna["aws"]["observed_uri"] == "s3://observed/rna/"
    assert merged["datasets"]["old_asset"]["status"] == "detached"
    assert warnings


def test_manifest_merge_adds_api_aws_uri_when_not_curated(monkeypatch):
    module = _load_refresher(monkeypatch)
    asset_id = "01234567-89ab-cdef-0123-456789abcdef"
    document = {"datasets": {}}
    metadata = {
        asset_id: {
            "name": "Pathology Data",
            "source_bucket": {"origin": "aws", "bucket": "bucket", "prefix": "prefix"},
        }
    }

    merged, warnings = module.merge_manifest(
        document,
        [module.Attachment(asset_id, "/data/pathology")],
        metadata,
    )

    entry = merged["datasets"]["pathology_data"]
    assert entry["aws"] == {
        "uri": "s3://bucket/prefix/",
        "provenance": "codeocean-api",
    }
    assert not warnings
    markdown = module.render_markdown(merged)
    assert "s3://bucket/prefix/" in markdown
    assert "/data/pathology" in markdown


def test_refresher_uses_canonical_code_ocean_token_name(monkeypatch):
    module = _load_refresher(monkeypatch)
    monkeypatch.setenv("CODEOCEAN_API_TOKEN", "canonical-secret")
    monkeypatch.setenv("CODEOCEAN_TOKEN", "legacy-secret")

    assert module._token_from_environment("CODEOCEAN_API_TOKEN") == "canonical-secret"

    monkeypatch.delenv("CODEOCEAN_API_TOKEN")
    assert module._token_from_environment("CODEOCEAN_API_TOKEN") is None


def test_refresher_has_no_undocumented_code_ocean_aliases():
    text = REFRESHER.read_text(encoding="utf-8")
    assert '"CODEOCEAN_TOKEN"' not in text
    assert 'os.environ.get("CO_DOMAIN")' not in text


def test_refresher_end_to_end_with_saved_api_metadata(tmp_path):
    yaml_package = pytest.importorskip("ruamel.yaml")
    asset_id = "01234567-89ab-cdef-0123-456789abcdef"
    code = tmp_path / "code"
    metadata = tmp_path / ".codeocean"
    responses = tmp_path / "api-responses"
    code.mkdir()
    metadata.mkdir()
    responses.mkdir()
    (metadata / "datasets.json").write_text(
        json.dumps({"datasets": [{"id": asset_id, "mount": "rna"}]}),
        encoding="utf-8",
    )
    (responses / f"{asset_id}.json").write_text(
        json.dumps(
            {
                "id": asset_id,
                "name": "RNA Data",
                "description": "API description",
                "source_bucket": {
                    "origin": "aws",
                    "bucket": "source-bucket",
                    "prefix": "project/rna",
                },
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REFRESHER),
            "--root",
            str(tmp_path),
            "--metadata-dir",
            str(responses),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    yaml = yaml_package.YAML(typ="safe")
    manifest = yaml.load((code / "datasets.yaml").read_text(encoding="utf-8"))
    entry = manifest["datasets"]["rna_data"]
    assert entry["mount"] == "/data/rna"
    assert entry["codeocean"]["id"] == asset_id
    assert entry["aws"]["uri"] == "s3://source-bucket/project/rna/"
    assert "RNA Data" not in result.stderr
    assert "s3://source-bucket/project/rna/" in (code / "DATASETS.md").read_text(encoding="utf-8")
