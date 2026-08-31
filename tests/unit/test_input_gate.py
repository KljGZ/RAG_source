from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from provtrust.execution.input_gate import validate_frozen_execution_inputs
from provtrust.execution.model_assets import build_model_asset_manifest


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _frozen_fixture(root: Path) -> dict[str, Any]:
    model_root = root / "models" / "Qwen3-fixture"
    model_root.mkdir(parents=True)
    (model_root / "weights.safetensors").write_bytes(b"fixture-weights")
    manifest = build_model_asset_manifest(
        model_root,
        model_id="Qwen/Qwen3-Fixture",
        source_platform="fixture",
        source_repository="Qwen/Qwen3-Fixture",
        source_revision="revision-1",
        upstream_huggingface_revision="a" * 40,
        license_name="Apache-2.0",
        captured_at=datetime(2026, 8, 31, tzinfo=UTC),
    )
    manifest_path = root / "configs/models/assets/qwen-fixture.manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8"
    )
    prompt_path = root / "prompts/frozen/answer.txt"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("Return JSON.\n", encoding="utf-8")
    dataset_path = root / "benchmark/smoke.jsonl"
    dataset_path.parent.mkdir(parents=True)
    dataset_path.write_text('{"fixture": true}\n', encoding="utf-8")
    dataset_manifest_path = root / "benchmark/manifests/smoke.yaml"
    _write_yaml(
        dataset_manifest_path,
        {"path": "benchmark/smoke.jsonl", "sha256": _sha256(dataset_path)},
    )
    registration_path = root / "configs/models/qwen-fixture-v0.yaml"
    _write_yaml(
        registration_path,
        {
            "schema_version": "1.0.0",
            "registration_id": "qwen-fixture-v0-target",
            "status": "frozen",
            "role": "target",
            "primary_judge_eligible": False,
            "provider": "hf",
            "inspect_model": "hf/Qwen/Qwen3-Fixture",
            "model_id": "Qwen/Qwen3-Fixture",
            "architecture": "Qwen3ForCausalLM",
            "license": "Apache-2.0",
            "parameter_count_billions": 1.0,
            "native_context_tokens": 1024,
            "config_max_position_embeddings": 1024,
            "inference_dtype": "bfloat16",
            "local_files_only": True,
            "trust_remote_code": False,
            "deployment_subdirectory": model_root.name,
            "snapshot": {
                "source_platform": "fixture",
                "repository": "Qwen/Qwen3-Fixture",
                "source_revision": "revision-1",
                "captured_at": "2026-08-31T00:00:00Z",
                "upstream_huggingface_revision": "a" * 40,
                "asset_manifest": "configs/models/assets/qwen-fixture.manifest.json",
                "asset_manifest_sha256": _sha256(manifest_path),
                "root_sha256": manifest.root_sha256,
                "file_count": manifest.file_count,
                "total_bytes": manifest.total_bytes,
            },
            "generation": {
                "enable_thinking": False,
                "do_sample": True,
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 20,
                "max_tokens": 16,
                "seeds": [7],
            },
            "system_prompt": {
                "path": "prompts/frozen/answer.txt",
                "sha256": _sha256(prompt_path),
            },
        },
    )
    model_args_path = root / "configs/models/qwen-fixture.local.yaml"
    _write_yaml(
        model_args_path,
        {
            "model_path": str(model_root),
            "tokenizer_path": str(model_root),
            "device": "cuda:0",
            "dtype": "auto",
            "local_files_only": True,
            "trust_remote_code": False,
            "low_cpu_mem_usage": True,
            "enable_thinking": False,
            "do_sample": True,
            "batch_size": 1,
        },
    )
    activation_path = root / "artifacts/system/compatibility.json"
    activation_path.parent.mkdir(parents=True)
    activation_path.write_text(
        json.dumps(
            {
                "status": "passed",
                "model_asset": {"root_sha256": manifest.root_sha256},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "model_registration": "configs/models/qwen-fixture-v0.yaml",
        "model_asset_manifest": "configs/models/assets/qwen-fixture.manifest.json",
        "model_args": "configs/models/qwen-fixture.local.yaml",
        "system_prompt": "prompts/frozen/answer.txt",
        "system_prompt_sha256": _sha256(prompt_path),
        "dataset_manifest": "benchmark/manifests/smoke.yaml",
        "activation_evidence": "artifacts/system/compatibility.json",
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "max_tokens": 16,
        "enable_thinking": False,
        "seed": 7,
        "inspect_command": [
            "inspect",
            "eval",
            "fixture-task",
            "-T",
            "dataset_path=benchmark/smoke.jsonl",
            "--model",
            "hf/Qwen/Qwen3-Fixture",
            "--model-config",
            "configs/models/qwen-fixture.local.yaml",
        ],
    }


def test_frozen_execution_gate_accepts_exact_inputs(tmp_path: Path) -> None:
    plan = _frozen_fixture(tmp_path)
    assert validate_frozen_execution_inputs(plan, tmp_path) == ()


def test_frozen_execution_gate_detects_weight_tampering(tmp_path: Path) -> None:
    plan = _frozen_fixture(tmp_path)
    (tmp_path / "models/Qwen3-fixture/weights.safetensors").write_bytes(b"tampered")
    assert "size_mismatch:weights.safetensors" in validate_frozen_execution_inputs(
        plan, tmp_path
    )


def test_frozen_execution_gate_rejects_online_model_args(tmp_path: Path) -> None:
    plan = _frozen_fixture(tmp_path)
    args_path = tmp_path / "configs/models/qwen-fixture.local.yaml"
    model_args = yaml.safe_load(args_path.read_text(encoding="utf-8"))
    model_args["local_files_only"] = False
    _write_yaml(args_path, model_args)
    assert "unsafe_or_mismatched_model_arg:local_files_only" in (
        validate_frozen_execution_inputs(plan, tmp_path)
    )
