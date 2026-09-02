from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from provtrust.datasets.io import read_jsonl


def test_snapshot_name_is_content_hash() -> None:
    documents = list(read_jsonl(Path("web_env/search_index/documents.jsonl")))
    assert documents
    for document in documents:
        relative = document.get("snapshot_path") or f"{document['snapshot_hash']}.txt"
        snapshot = Path("web_env/source_snapshots") / relative
        assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == document["snapshot_hash"]


def test_frozen_prompt_hashes() -> None:
    manifest = json.loads(Path("prompts/frozen/MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["prompts"]:
        assert hashlib.sha256(Path(entry["path"]).read_bytes()).hexdigest() == entry["sha256"]


def _assert_dataset_payload(manifest: dict[str, object]) -> None:
    for path_field, hash_field in (
        ("path", "sha256"),
        ("config_path", "config_sha256"),
        ("splits_path", "splits_sha256"),
        ("audit_path", "audit_sha256"),
    ):
        path = Path(manifest[path_field])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[hash_field]
    audit = json.loads(Path(manifest["audit_path"]).read_text(encoding="utf-8"))
    assert audit["status"] == "passed"
    assert audit["stimulus_audit"]["errors"] == []
    assert audit["stimulus_audit"]["gold_leakage_detected"] is False


def test_v0_paired_dataset_and_identification_artifacts_are_frozen() -> None:
    v1_path = Path("benchmark/manifests/v0-paired-v1.yaml")
    v1 = yaml.safe_load(v1_path.read_text(encoding="utf-8"))
    _assert_dataset_payload(v1)
    history = json.loads(
        Path("benchmark/manifests/V0_HISTORY.json").read_text(encoding="utf-8")
    )
    records = {row["path"]: row for row in history["historical_manifests"]}
    for version in ("v1", "v2", "v3"):
        manifest_path = Path(f"benchmark/manifests/v0-paired-{version}.yaml")
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        _assert_dataset_payload(manifest)
        record = records[manifest_path.as_posix()]
        assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == record["sha256"]
        for relative, expected in manifest["source_code_sha256"].items():
            source = subprocess.run(
                ["git", "show", f"{record['execution_git_revision']}:{relative}"],
                check=True,
                capture_output=True,
            ).stdout
            assert hashlib.sha256(source).hexdigest() == expected
