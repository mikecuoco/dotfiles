#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["ruamel.yaml>=0.18,<0.19"]
# ///
"""Refresh a capsule's dataset manifest from Code Ocean attachment metadata.

The script preserves manually curated YAML fields, optionally enriches attached
assets through the Code Ocean API, marks missing attachments as detached, and
regenerates DATASETS.md. It never edits .codeocean/datasets.json.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap
except ImportError as exc:  # pragma: no cover - exercised by invocation environment
    raise SystemExit(
        "ruamel.yaml is required; run this helper with `uv run --script`"
    ) from exc


ID_KEYS = ("id", "data_asset_id", "dataAssetId", "dataset_id", "datasetId")
MOUNT_KEYS = ("mount", "mount_path", "mountPath", "mount_name", "mountName")
NAME_KEYS = ("name", "display_name", "displayName")
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@dataclass(frozen=True)
class Attachment:
    asset_id: str
    mount: str | None = None
    name: str | None = None


def _first_text(value: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        candidate = value.get(key)
        if candidate is not None and str(candidate).strip():
            return str(candidate).strip()
    return None


def _looks_like_asset_id(value: str) -> bool:
    return bool(UUID_RE.fullmatch(value))


def _normalize_mount(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().rstrip("/")
    if not cleaned:
        return None
    if cleaned.startswith("/"):
        return cleaned
    return f"/data/{cleaned.lstrip('/')}"


def extract_attachments(document: Any) -> list[Attachment]:
    """Extract attachments from known and legacy datasets.json shapes."""
    found: dict[str, Attachment] = {}

    def remember(asset_id: str, mount: str | None, name: str | None) -> None:
        asset_id = asset_id.strip()
        if not asset_id:
            return
        normalized = Attachment(asset_id, _normalize_mount(mount), name)
        previous = found.get(asset_id)
        if previous is None:
            found[asset_id] = normalized
            return
        found[asset_id] = Attachment(
            asset_id,
            normalized.mount or previous.mount,
            normalized.name or previous.name,
        )

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            explicit_id = _first_text(node, ID_KEYS)
            if explicit_id:
                remember(
                    explicit_id,
                    _first_text(node, MOUNT_KEYS),
                    _first_text(node, NAME_KEYS),
                )

            for key, child in node.items():
                key_text = str(key)
                if _looks_like_asset_id(key_text) and not explicit_id:
                    if isinstance(child, Mapping):
                        remember(
                            key_text,
                            _first_text(child, MOUNT_KEYS),
                            _first_text(child, NAME_KEYS),
                        )
                    elif isinstance(child, str):
                        remember(key_text, child, None)
                if isinstance(child, (Mapping, list, tuple)):
                    visit(child)
        elif isinstance(node, (list, tuple)):
            for child in node:
                visit(child)

    visit(document)
    return sorted(found.values(), key=lambda item: (item.mount or "", item.asset_id))


def locate_code_dir(root: Path) -> Path:
    root = root.resolve()
    candidate = root / "code"
    if candidate.is_dir():
        return candidate
    if root.name == "code" or (root / "datasets.yaml").exists():
        return root
    raise FileNotFoundError(f"could not locate code/ beneath {root}")


def locate_datasets_json(root: Path, code_dir: Path) -> Path:
    candidates = [
        root / ".codeocean" / "datasets.json",
        code_dir / ".codeocean" / "datasets.json",
        code_dir.parent / ".codeocean" / "datasets.json",
    ]
    if root.resolve() == Path("/"):
        candidates.append(Path("/.codeocean/datasets.json"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    attempted = ", ".join(str(path) for path in dict.fromkeys(candidates))
    raise FileNotFoundError(f"could not locate .codeocean/datasets.json; tried {attempted}")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def _unwrap_api_document(document: Any) -> Mapping[str, Any]:
    if not isinstance(document, Mapping):
        raise ValueError("API response is not a JSON object")
    for wrapper in ("data_asset", "dataAsset", "result"):
        nested = document.get(wrapper)
        if isinstance(nested, Mapping):
            return nested
    return document


def load_saved_metadata(directory: Path, asset_id: str) -> Mapping[str, Any]:
    if Path(asset_id).name != asset_id:
        raise ValueError(f"unsafe asset ID for metadata filename: {asset_id!r}")
    path = directory / f"{asset_id}.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    return _unwrap_api_document(_load_json(path))


def fetch_asset_metadata(domain: str, token: str, asset_id: str) -> Mapping[str, Any]:
    base = domain.strip().rstrip("/")
    if not base.startswith(("https://", "http://")):
        base = f"https://{base}"
    encoded_id = urllib.parse.quote(asset_id, safe="")
    request = urllib.request.Request(f"{base}/api/v1/data_assets/{encoded_id}")
    credentials = base64.b64encode(f"{token}:".encode()).decode()
    request.add_header("Authorization", f"Basic {credentials}")
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return _unwrap_api_document(json.load(response))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return result or "dataset"


def _new_key(
    attachment: Attachment,
    metadata: Mapping[str, Any] | None,
    existing: Mapping[str, Any],
) -> str:
    source = ""
    if metadata:
        source = str(metadata.get("name") or "")
    source = source or attachment.name or (attachment.mount or "").rsplit("/", 1)[-1]
    source = source or attachment.asset_id[:8]
    base = _slug(source)
    candidate = base
    suffix = 2
    while candidate in existing:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def _mapping(value: Any) -> MutableMapping[str, Any]:
    return value if isinstance(value, MutableMapping) else CommentedMap()


def _find_key_by_asset_id(datasets: Mapping[str, Any], asset_id: str) -> str | None:
    for key, raw in datasets.items():
        if not isinstance(raw, Mapping):
            continue
        codeocean = raw.get("codeocean")
        if isinstance(codeocean, Mapping) and str(codeocean.get("id", "")) == asset_id:
            return str(key)
    return None


def _source_bucket_uri(metadata: Mapping[str, Any]) -> str | None:
    source = metadata.get("source_bucket")
    if not isinstance(source, Mapping) or str(source.get("origin", "")).lower() != "aws":
        return None
    bucket = str(source.get("bucket") or "").strip().strip("/")
    prefix = str(source.get("prefix") or "").strip().strip("/")
    if not bucket:
        return None
    return f"s3://{bucket}/{prefix}/" if prefix else f"s3://{bucket}/"


def merge_manifest(
    document: MutableMapping[str, Any],
    attachments: Sequence[Attachment],
    metadata_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[MutableMapping[str, Any], list[str]]:
    """Merge observed attachments while preserving curated manifest fields."""
    warnings: list[str] = []
    datasets = _mapping(document.get("datasets"))
    document["datasets"] = datasets
    attached_ids = {item.asset_id for item in attachments}

    for key, raw in datasets.items():
        if not isinstance(raw, MutableMapping):
            warnings.append(f"{key}: entry is not a mapping; left unchanged")
            continue
        codeocean = raw.get("codeocean")
        if isinstance(codeocean, Mapping):
            asset_id = str(codeocean.get("id") or "")
            if asset_id and asset_id not in attached_ids:
                raw["status"] = "detached"

    for attachment in attachments:
        metadata = metadata_by_id.get(attachment.asset_id)
        key = _find_key_by_asset_id(datasets, attachment.asset_id)
        if key is None:
            key = _new_key(attachment, metadata, datasets)
            datasets[key] = CommentedMap()

        entry = _mapping(datasets[key])
        datasets[key] = entry
        entry["status"] = "attached"

        observed_mount = attachment.mount
        if not observed_mount and metadata:
            observed_mount = _normalize_mount(str(metadata.get("mount") or ""))
        if observed_mount:
            entry["mount"] = observed_mount

        codeocean = _mapping(entry.get("codeocean"))
        entry["codeocean"] = codeocean
        codeocean["id"] = attachment.asset_id
        if metadata:
            for field in ("name", "type", "state"):
                value = metadata.get(field)
                if value not in (None, ""):
                    codeocean[field] = value
            description = metadata.get("description")
            if description and not entry.get("description"):
                entry["description"] = description

            observed_uri = _source_bucket_uri(metadata)
            if observed_uri:
                aws = _mapping(entry.get("aws"))
                entry["aws"] = aws
                current_uri = str(aws.get("uri") or "")
                provenance = str(aws.get("provenance") or "")
                curated = bool(current_uri) and provenance not in {
                    "codeocean-api",
                    "codeocean_api",
                }
                if curated and current_uri != observed_uri:
                    aws["observed_uri"] = observed_uri
                    warnings.append(
                        f"{key}: curated AWS URI differs from Code Ocean source_bucket"
                    )
                else:
                    aws["uri"] = observed_uri
                    aws["provenance"] = "codeocean-api"
                    aws.pop("observed_uri", None)

    return document, warnings


def load_manifest(path: Path) -> tuple[YAML, MutableMapping[str, Any]]:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    if not path.exists():
        document: MutableMapping[str, Any] = CommentedMap()
        document["datasets"] = CommentedMap()
        return yaml, document
    try:
        loaded = yaml.load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid YAML in {path}: {exc}") from exc
    if loaded is None:
        loaded = CommentedMap()
    if not isinstance(loaded, MutableMapping):
        raise ValueError(f"{path} must contain a top-level mapping")
    if "datasets" in loaded and not isinstance(loaded["datasets"], MutableMapping):
        raise ValueError(f"{path}: top-level 'datasets' must be a mapping")
    return yaml, loaded


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        temp_path.replace(path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def dump_yaml(yaml: YAML, document: MutableMapping[str, Any]) -> str:
    from io import StringIO

    stream = StringIO()
    yaml.dump(document, stream)
    return stream.getvalue()


def _markdown_cell(value: Any) -> str:
    if value in (None, ""):
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(document: Mapping[str, Any]) -> str:
    lines = [
        "# Datasets",
        "",
        "Generated from `datasets.yaml`. Edit the YAML manifest, then refresh this view.",
        "",
        "| Key | Status | Mount | Code Ocean asset | AWS source | Description |",
        "|---|---|---|---|---|---|",
    ]
    datasets = document.get("datasets", {})
    if not isinstance(datasets, Mapping):
        datasets = {}
    for key, raw in datasets.items():
        entry = raw if isinstance(raw, Mapping) else {}
        codeocean = entry.get("codeocean", {})
        aws = entry.get("aws", {})
        asset_id = codeocean.get("id") if isinstance(codeocean, Mapping) else None
        aws_uri = aws.get("uri") if isinstance(aws, Mapping) else None
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    key,
                    entry.get("status"),
                    entry.get("mount"),
                    asset_id,
                    aws_uri,
                    entry.get("description"),
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _token_from_environment(primary: str) -> str | None:
    for name in dict.fromkeys((primary, "CODEOCEAN_API_TOKEN")):
        value = os.environ.get(name)
        if value:
            return value
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="capsule or code root")
    parser.add_argument("--datasets-json", type=Path, help="override .codeocean/datasets.json")
    parser.add_argument("--manifest", type=Path, help="override code/datasets.yaml")
    parser.add_argument("--markdown", type=Path, help="override code/DATASETS.md")
    parser.add_argument("--domain", help="Code Ocean domain; defaults to CODEOCEAN_DOMAIN")
    parser.add_argument("--token-env", default="CODEOCEAN_API_TOKEN")
    parser.add_argument("--metadata-dir", type=Path, help="directory of saved <asset-id>.json responses")
    parser.add_argument("--offline", action="store_true", help="skip all API enrichment")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = args.root.resolve()
        code_dir = locate_code_dir(root)
        datasets_json = args.datasets_json or locate_datasets_json(root, code_dir)
        manifest_path = args.manifest or code_dir / "datasets.yaml"
        markdown_path = args.markdown or code_dir / "DATASETS.md"
        attachments = extract_attachments(_load_json(datasets_json))
        if not attachments:
            print(f"warning: no attached Data Asset IDs found in {datasets_json}", file=sys.stderr)

        metadata_by_id: dict[str, Mapping[str, Any]] = {}
        warnings: list[str] = []
        domain = args.domain or os.environ.get("CODEOCEAN_DOMAIN")
        token = _token_from_environment(args.token_env)
        for attachment in attachments:
            try:
                if args.metadata_dir:
                    metadata_by_id[attachment.asset_id] = load_saved_metadata(
                        args.metadata_dir, attachment.asset_id
                    )
                elif not args.offline and domain and token:
                    metadata_by_id[attachment.asset_id] = fetch_asset_metadata(
                        domain, token, attachment.asset_id
                    )
            except (OSError, ValueError, RuntimeError) as exc:
                warnings.append(f"{attachment.asset_id}: metadata unavailable ({exc})")

        if not args.offline and not args.metadata_dir:
            if not domain:
                warnings.append("API enrichment skipped: CODEOCEAN_DOMAIN is not set")
            elif not token:
                warnings.append(
                    f"API enrichment skipped: token variable {args.token_env} is not set"
                )

        yaml, document = load_manifest(manifest_path)
        document, merge_warnings = merge_manifest(document, attachments, metadata_by_id)
        warnings.extend(merge_warnings)
        yaml_content = dump_yaml(yaml, document)
        markdown_content = render_markdown(document)

        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        action = "would refresh" if args.dry_run else "refreshed"
        if not args.dry_run:
            _atomic_write(manifest_path, yaml_content)
            _atomic_write(markdown_path, markdown_content)
        print(
            f"{action} {len(attachments)} attached dataset(s): "
            f"{manifest_path} and {markdown_path}"
        )
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
