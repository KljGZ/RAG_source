"""Create and verify portable, content-addressed model snapshot manifests."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from provtrust.execution.atomic_io import atomic_write_json
from provtrust.execution.model_assets import (
    ModelAssetManifest,
    build_model_asset_manifest,
    verify_model_asset_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--model-id", required=True)
    create.add_argument("--source-platform", required=True)
    create.add_argument("--source-repository", required=True)
    create.add_argument("--source-revision", required=True)
    create.add_argument("--upstream-huggingface-revision")
    create.add_argument("--license", dest="license_name", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    if args.action == "create":
        manifest = build_model_asset_manifest(
            args.root,
            model_id=args.model_id,
            source_platform=args.source_platform,
            source_repository=args.source_repository,
            source_revision=args.source_revision,
            upstream_huggingface_revision=args.upstream_huggingface_revision,
            license_name=args.license_name,
            captured_at=datetime.now(UTC),
        )
        digest = atomic_write_json(args.output, manifest.model_dump(mode="json"))
        print(
            json.dumps(
                {
                    "created": True,
                    "manifest": str(args.output),
                    "manifest_sha256": digest,
                    "root_sha256": manifest.root_sha256,
                    "file_count": manifest.file_count,
                    "total_bytes": manifest.total_bytes,
                },
                indent=2,
            )
        )
        return 0

    manifest = ModelAssetManifest.model_validate_json(args.manifest.read_text(encoding="utf-8"))
    failures = verify_model_asset_manifest(args.root, manifest)
    print(
        json.dumps(
            {
                "verified": not failures,
                "root": str(args.root),
                "root_sha256": manifest.root_sha256,
                "failures": failures,
            },
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
