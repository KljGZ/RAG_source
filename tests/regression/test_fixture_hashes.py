from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml


def test_snapshot_name_is_content_hash() -> None:
    index = json.loads(Path("web_env/search_index/documents.jsonl").read_text(encoding="utf-8"))
    snapshot = Path("web_env/source_snapshots") / f"{index['snapshot_hash']}.txt"
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == index["snapshot_hash"]


def test_frozen_prompt_hashes() -> None:
    manifest = json.loads(Path("prompts/frozen/MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["prompts"]:
        assert hashlib.sha256(Path(entry["path"]).read_bytes()).hexdigest() == entry["sha256"]


def test_v0_paired_dataset_and_identification_artifacts_are_frozen() -> None:
    manifest = yaml.safe_load(
        Path("benchmark/manifests/v0-paired-v1.yaml").read_text(encoding="utf-8")
    )
    for path_field, hash_field in (
        ("path", "sha256"),
        ("config_path", "config_sha256"),
        ("splits_path", "splits_sha256"),
        ("audit_path", "audit_sha256"),
    ):
        path = Path(manifest[path_field])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[hash_field]
    for relative, expected in manifest["source_code_sha256"].items():
        assert hashlib.sha256(Path(relative).read_bytes()).hexdigest() == expected
    audit = json.loads(Path(manifest["audit_path"]).read_text(encoding="utf-8"))
    assert audit["status"] == "passed"
    assert audit["stimulus_audit"]["errors"] == []
    assert audit["stimulus_audit"]["gold_leakage_detected"] is False
