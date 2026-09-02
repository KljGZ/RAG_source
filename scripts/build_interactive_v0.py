"""Build frozen Track-E datasets and the isolated interactive tool environment."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from provtrust.datasets.interactive_v0 import (
    ENVIRONMENT_VERSION,
    InteractivePolicy,
    build_interactive_assets,
)
from provtrust.datasets.io import read_jsonl
from provtrust.datasets.v0_corpus import V0CorpusSpec
from provtrust.execution.atomic_io import atomic_write_bytes, atomic_write_json, sha256_file


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML object: {path}")
    return value


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        + b"\n"
        for row in rows
    )


def _yaml_bytes(value: dict[str, Any]) -> bytes:
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True).encode("utf-8")


def _fixture_documents(path: Path) -> list[dict[str, Any]]:
    return [
        row
        for row in read_jsonl(path)
        if row.get("condition") == "neutral_fixture"
    ]


def _fixture_sources(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise TypeError("source registry must contain an array")
    return [
        row
        for row in value
        if isinstance(row, dict) and row.get("source_id") == "controlled-fixture"
    ]


def _fixture_identifiers(path: Path) -> dict[str, dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("identifier registry must contain an object")
    return {
        key: row
        for key, row in value.items()
        if key.startswith("FIXTURE-") and isinstance(row, dict)
    }


def _scientific_fingerprint(row: dict[str, Any]) -> str:
    value = json.loads(json.dumps(row))
    value.pop("item_id", None)
    value["tool_condition"] = "policy_specific"
    value["verification_required"] = "policy_specific"
    metadata = value.get("metadata")
    if isinstance(metadata, dict):
        metadata["interactive_policy"] = "policy_specific"
    vector = value.get("intervention_vector")
    if isinstance(vector, dict):
        vector["interactive_policy"] = "policy_specific"
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _risk_fingerprint(row: dict[str, Any]) -> str:
    value = json.loads(json.dumps(row))
    value.pop("item_id", None)
    claim = value.get("claim")
    if isinstance(claim, dict):
        claim["claim_id"] = "risk_specific"
        claim["risk_level"] = "risk_specific"
    value["tool_condition"] = "risk_specific"
    value["verification_required"] = "risk_specific"
    metadata = value.get("metadata")
    if isinstance(metadata, dict):
        metadata["risk_condition"] = "risk_specific"
    vector = value.get("intervention_vector")
    if isinstance(vector, dict):
        vector["risk_level"] = "risk_specific"
    for evidence in value.get("evidence", []):
        if isinstance(evidence, dict):
            evidence["claim_id"] = "risk_specific"
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _build_split_rows(base_splits: Path) -> list[dict[str, Any]]:
    rows = list(read_jsonl(base_splits))
    by_family: dict[str, str] = {}
    for row in rows:
        family_id = str(row["family_id"])
        split = str(row["split"])
        previous = by_family.setdefault(family_id, split)
        if previous != split:
            raise ValueError(f"base split crosses family: {family_id}")
    return [
        {"family_id": family_id, "split": split}
        for family_id, split in sorted(by_family.items())
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("configs/datasets/v0_interactive_v1.yaml")
    )
    args = parser.parse_args()
    config = _load_yaml(args.config)
    if config.get("environment_version") != ENVIRONMENT_VERSION:
        raise ValueError("interactive environment version does not match builder")
    base_path = Path(str(config["base_corpus_config"]))
    base_spec = V0CorpusSpec.model_validate(_load_yaml(base_path))
    policies = tuple(InteractivePolicy(value) for value in config["policies"])

    assets_by_policy = {
        policy: build_interactive_assets(base_spec, policy) for policy in policies
    }
    shared = assets_by_policy[policies[0]]
    for assets in assets_by_policy.values():
        if assets.documents != shared.documents or assets.snapshots != shared.snapshots:
            raise ValueError("tool assets must remain invariant across policies")
        if assets.source_registry != shared.source_registry:
            raise ValueError("source registry must remain invariant across policies")
        if assets.identifier_registry != shared.identifier_registry:
            raise ValueError("identifier registry must remain invariant across policies")
        if assets.provenance_registry != shared.provenance_registry:
            raise ValueError("provenance registry must remain invariant across policies")

    index_path = Path("web_env/search_index/documents.jsonl")
    source_path = Path("web_env/canonical_sources/registry.json")
    identifiers_path = Path("web_env/canonical_sources/identifiers.json")
    provenance_path = Path("web_env/canonical_sources/provenance-v1.json")
    snapshot_root = Path("web_env/source_snapshots")
    fixture_documents = _fixture_documents(index_path)
    fixture_sources = _fixture_sources(source_path)
    fixture_identifiers = _fixture_identifiers(identifiers_path)

    documents = sorted(
        [*fixture_documents, *shared.documents], key=lambda row: str(row["document_id"])
    )
    sources = sorted(
        [*fixture_sources, *shared.source_registry], key=lambda row: str(row["source_id"])
    )
    identifiers = {**fixture_identifiers, **shared.identifier_registry}
    atomic_write_bytes(index_path, _jsonl_bytes(documents))
    atomic_write_json(source_path, sources)
    atomic_write_json(identifiers_path, identifiers)
    atomic_write_json(provenance_path, shared.provenance_registry)
    for relative, content in shared.snapshots.items():
        atomic_write_bytes(snapshot_root / relative, content)

    referenced_snapshot_names = {
        str(document.get("snapshot_path") or f"{document['snapshot_hash']}.txt")
        for document in documents
    }
    snapshot_entries: list[dict[str, Any]] = []
    for relative in sorted(referenced_snapshot_names):
        path = snapshot_root / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        snapshot_entries.append(
            {
                "path": path.as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    snapshot_manifest_path = snapshot_root / "MANIFEST.json"
    atomic_write_json(
        snapshot_manifest_path,
        {
            "schema_version": "1.0.0",
            "environment_version": ENVIRONMENT_VERSION,
            "strict_root": snapshot_root.as_posix(),
            "files": snapshot_entries,
        },
    )

    tool_files = [
        index_path,
        source_path,
        identifiers_path,
        provenance_path,
        snapshot_manifest_path,
        *(Path(str(row["path"])) for row in snapshot_entries),
    ]
    tool_manifest_path = Path("benchmark/manifests/interactive-v1-tools.yaml")
    tool_manifest = {
        "schema_version": "1.0.0",
        "environment_version": ENVIRONMENT_VERSION,
        "isolated": True,
        "network_policy": "loopback_or_offline_only",
        "search_index_path": index_path.as_posix(),
        "snapshot_root": snapshot_root.as_posix(),
        "source_registry_path": source_path.as_posix(),
        "identifier_registry_path": identifiers_path.as_posix(),
        "provenance_registry_path": provenance_path.as_posix(),
        "snapshot_manifest_path": snapshot_manifest_path.as_posix(),
        "files": [
            {
                "path": path.as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in tool_files
        ],
    }
    atomic_write_bytes(tool_manifest_path, _yaml_bytes(tool_manifest))

    split_path = Path("benchmark/splits/v0-interactive-v1.jsonl")
    split_rows = _build_split_rows(Path("benchmark/splits/v0-paired-v1.jsonl"))
    atomic_write_bytes(split_path, _jsonl_bytes(split_rows))

    dataset_paths: dict[InteractivePolicy, Path] = {}
    dataset_rows: dict[InteractivePolicy, list[dict[str, Any]]] = {}
    for policy, assets in assets_by_policy.items():
        rows = [trial.model_dump(mode="json") for trial in assets.trials]
        path = Path(f"benchmark/synthetic/v0-interactive-v1-{policy.value}.jsonl")
        atomic_write_bytes(path, _jsonl_bytes(rows))
        dataset_paths[policy] = path
        dataset_rows[policy] = rows

    first_fingerprints = [_scientific_fingerprint(row) for row in dataset_rows[policies[0]]]
    policy_invariance = all(
        [_scientific_fingerprint(row) for row in dataset_rows[policy]] == first_fingerprints
        for policy in policies[1:]
    )
    risk_pairing = True
    for policy, rows in dataset_rows.items():
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            metadata = row["metadata"]
            grouped.setdefault(str(metadata["paired_scene_id"]), []).append(row)
        if len(grouped) != int(config["family_count"]) * int(config["scenes_per_family"]):
            risk_pairing = False
        for pair in grouped.values():
            risks = {str(row["metadata"]["risk_condition"]) for row in pair}
            if len(pair) != 2 or risks != {"low", "high"}:
                risk_pairing = False
            elif len({_risk_fingerprint(row) for row in pair}) != 1:
                risk_pairing = False

    expected_items = int(config["items_per_policy"])
    observed_counts = {policy.value: len(rows) for policy, rows in dataset_rows.items()}
    candidate_balance = {
        policy.value: dict(
            sorted(Counter(bool(row["candidate_answer"]) for row in rows).items())
        )
        for policy, rows in dataset_rows.items()
    }
    audit_path = Path("artifacts/system/V0_INTERACTIVE_DATASET_AUDIT.json")
    audit = {
        "schema_version": "1.0.0",
        "status": "passed"
        if policy_invariance
        and risk_pairing
        and all(count == expected_items for count in observed_counts.values())
        else "failed",
        "protocol": "interactive_verification_v1",
        "environment_version": ENVIRONMENT_VERSION,
        "policy_invariance": policy_invariance,
        "exact_low_high_risk_pairing": risk_pairing,
        "family_count": len(split_rows),
        "scenario_count": int(config["scenes_per_family"]),
        "items_per_policy": observed_counts,
        "candidate_answer_balance": candidate_balance,
        "tool_document_count": len(documents),
        "interactive_snapshot_count": len(shared.snapshots),
        "referenced_snapshot_count": len(snapshot_entries),
        "source_registry_count": len(sources),
        "identifier_registry_count": len(identifiers),
        "dataset_sha256": {
            policy.value: sha256_file(path) for policy, path in dataset_paths.items()
        },
        "tool_environment_manifest_sha256": sha256_file(tool_manifest_path),
    }
    atomic_write_json(audit_path, audit)
    if audit["status"] != "passed":
        raise RuntimeError("interactive dataset audit failed")

    source_hashes = {
        "src/provtrust/datasets/interactive_v0.py": sha256_file(
            Path("src/provtrust/datasets/interactive_v0.py")
        ),
        "scripts/build_interactive_v0.py": sha256_file(
            Path("scripts/build_interactive_v0.py")
        ),
    }
    for policy, path in dataset_paths.items():
        manifest_path = Path(
            f"benchmark/manifests/v0-interactive-v1-{policy.value}.yaml"
        )
        manifest = {
            "schema_version": "1.0.0",
            "dataset_id": f"provtrust-v0-interactive-v1-{policy.value}",
            "purpose": config["purpose"],
            "protocol": "interactive_verification_v1",
            "environment_version": ENVIRONMENT_VERSION,
            "interactive_policy": policy.value,
            "builder": "provtrust.datasets.interactive_v0:build_interactive_assets",
            "builder_version": ENVIRONMENT_VERSION,
            "seed": int(config["seed"]),
            "path": path.as_posix(),
            "sha256": sha256_file(path),
            "config_path": args.config.as_posix(),
            "config_sha256": sha256_file(args.config),
            "splits_path": split_path.as_posix(),
            "splits_sha256": sha256_file(split_path),
            "audit_path": audit_path.as_posix(),
            "audit_sha256": sha256_file(audit_path),
            "tool_environment_manifest": tool_manifest_path.as_posix(),
            "tool_environment_manifest_sha256": sha256_file(tool_manifest_path),
            "source_code_sha256": source_hashes,
            "license": config["license"],
            "redistributable": bool(config["redistributable"]),
            "contains_fabricated_real_world_claims": False,
            "family_count": int(config["family_count"]),
            "scenario_count": int(config["scenes_per_family"]),
            "risk_levels": list(config["risk_levels"]),
            "item_count": len(dataset_rows[policy]),
        }
        atomic_write_bytes(manifest_path, _yaml_bytes(manifest))

    print(
        json.dumps(
            {
                "status": audit["status"],
                "datasets": {
                    policy.value: {
                        "path": dataset_paths[policy].as_posix(),
                        "sha256": sha256_file(dataset_paths[policy]),
                    }
                    for policy in policies
                },
                "tool_environment_manifest": tool_manifest_path.as_posix(),
                "tool_environment_manifest_sha256": sha256_file(tool_manifest_path),
                "audit": audit_path.as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
