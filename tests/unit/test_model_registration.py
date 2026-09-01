from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from provtrust.execution.model_assets import ModelAssetManifest
from provtrust.registries.models import FrozenModelRegistration


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_qwen_v0_registration_matches_frozen_assets_and_prompt() -> None:
    config_path = Path("configs/models/qwen3-14b-v0.yaml")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    registration = FrozenModelRegistration.model_validate(raw)
    manifest_path = Path(registration.snapshot.asset_manifest)
    manifest = ModelAssetManifest.model_validate(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )

    assert _sha256(manifest_path) == registration.snapshot.asset_manifest_sha256
    assert manifest.root_sha256 == registration.snapshot.root_sha256
    assert manifest.file_count == registration.snapshot.file_count
    assert manifest.total_bytes == registration.snapshot.total_bytes
    assert _sha256(Path(registration.system_prompt.path)) == registration.system_prompt.sha256
    assert registration.generation.enable_thinking is False
    assert registration.primary_judge_eligible is False


def test_static_qwen_registration_uses_deterministic_decoding() -> None:
    raw = yaml.safe_load(
        Path("configs/models/qwen3-14b-static-v0.yaml").read_text(encoding="utf-8")
    )
    registration = FrozenModelRegistration.model_validate(raw)
    assert registration.generation.do_sample is False
    assert registration.generation.temperature == 0.0
    assert registration.system_prompt.sha256 == (
        "450e6eaa85df17643f17fab17840d4b8cb99dc349fb181e3d2d2ed91fb2c14dc"
    )


def test_static_phi4_registration_matches_frozen_assets() -> None:
    config_path = Path("configs/models/phi-4-static-v0.yaml")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    registration = FrozenModelRegistration.model_validate(raw)
    manifest_path = Path(registration.snapshot.asset_manifest)
    manifest = ModelAssetManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )

    assert registration.role == "secondary_target"
    assert registration.architecture == "Phi3ForCausalLM"
    assert registration.generation.do_sample is False
    assert registration.generation.temperature == 0.0
    assert registration.trust_remote_code is False
    assert _sha256(manifest_path) == registration.snapshot.asset_manifest_sha256
    assert manifest.source_revision == registration.snapshot.source_revision
    assert manifest.root_sha256 == registration.snapshot.root_sha256
    assert manifest.file_count == registration.snapshot.file_count
    assert manifest.total_bytes == registration.snapshot.total_bytes
