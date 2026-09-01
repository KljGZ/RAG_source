from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from provtrust.execution.model_assets import (
    ModelAssetFile,
    ModelAssetManifest,
    build_model_asset_manifest,
    verify_model_asset_manifest,
)


def _manifest(root: Path) -> ModelAssetManifest:
    return build_model_asset_manifest(
        root,
        model_id="fixture/model",
        source_platform="fixture",
        source_repository="fixture/model",
        source_revision="revision-1",
        upstream_huggingface_revision=None,
        license_name="Apache-2.0",
        captured_at=datetime(2026, 8, 31, tzinfo=UTC),
    )


def test_model_snapshot_round_trip_and_tamper_detection(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "weights.safetensors").write_bytes(b"model-fixture")
    manifest = _manifest(tmp_path)

    assert manifest.file_count == 2
    assert verify_model_asset_manifest(tmp_path, manifest) == ()

    (tmp_path / "weights.safetensors").write_bytes(b"tampered-model")
    assert verify_model_asset_manifest(tmp_path, manifest) == (
        "size_mismatch:weights.safetensors",
    )


def test_model_snapshot_detects_unexpected_files_and_ignores_hub_cache(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text("{}\n", encoding="utf-8")
    cache = tmp_path / ".cache"
    cache.mkdir()
    (cache / "transfer-state").write_text("mutable", encoding="utf-8")
    manifest = _manifest(tmp_path)
    assert manifest.file_count == 1

    (tmp_path / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    assert verify_model_asset_manifest(tmp_path, manifest) == ("unexpected:unexpected.txt",)


def test_model_asset_path_escape_is_rejected() -> None:
    with pytest.raises(ValidationError, match="normalized and relative"):
        ModelAssetFile(path="../weights.bin", bytes=1, sha256="0" * 64)


def test_model_manifest_rejects_duplicate_paths() -> None:
    record = ModelAssetFile(path="weights.bin", bytes=1, sha256="0" * 64)
    with pytest.raises(ValidationError, match="unique"):
        ModelAssetManifest(
            model_id="fixture/model",
            source_platform="fixture",
            source_repository="fixture/model",
            source_revision="revision-1",
            license="Apache-2.0",
            captured_at=datetime(2026, 8, 31, tzinfo=UTC),
            root_name="fixture",
            file_count=2,
            total_bytes=2,
            files=(record, record),
            root_sha256="0" * 64,
        )


def test_modelscope_downloader_metadata_is_not_part_of_snapshot(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".msc").write_text("mutable downloader state", encoding="utf-8")
    (tmp_path / ".mv").write_text("master", encoding="utf-8")
    temporary = tmp_path / "._____temp"
    temporary.mkdir()
    (temporary / "partial").write_bytes(b"incomplete")

    manifest = _manifest(tmp_path)

    assert tuple(record.path for record in manifest.files) == ("config.json",)
    assert verify_model_asset_manifest(tmp_path, manifest) == ()
