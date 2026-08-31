"""Build and audit the deterministic V0 paired synthetic corpus."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from provtrust.datasets.split import assign_grouped_splits
from provtrust.datasets.stimulus_audit import audit_paired_stimuli
from provtrust.datasets.v0_corpus import V0CorpusSpec, build_v0_corpus
from provtrust.datasets.validate import validate_trials
from provtrust.execution.atomic_io import atomic_write_bytes, atomic_write_json, sha256_file


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        + b"\n"
        for row in rows
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("configs/datasets/v0_paired_v1.yaml")
    )
    parser.add_argument(
        "--dataset", type=Path, default=Path("benchmark/synthetic/v0-paired-v1.jsonl")
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("benchmark/manifests/v0-paired-v1.yaml")
    )
    parser.add_argument(
        "--splits", type=Path, default=Path("benchmark/splits/v0-paired-v1.jsonl")
    )
    parser.add_argument(
        "--audit", type=Path, default=Path("artifacts/system/V0_PAIRED_DATASET_AUDIT.json")
    )
    args = parser.parse_args()
    root = Path.cwd().resolve()
    config_value = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    spec = V0CorpusSpec.model_validate(config_value)
    trials = build_v0_corpus(spec)
    dataset_hash = atomic_write_bytes(
        args.dataset,
        _jsonl([trial.model_dump(mode="json") for trial in trials]),
    )
    assignments = assign_grouped_splits(trials, seed=spec.seed)
    split_rows = [
        {
            "schema_version": "1.0.0",
            "item_id": assignment.item_id,
            "component_id": assignment.component_id,
            "split": assignment.split,
            "seed": spec.seed,
            "builder_version": spec.builder_version,
            "source_dataset_sha256": dataset_hash,
        }
        for assignment in assignments
    ]
    split_hash = atomic_write_bytes(args.splits, _jsonl(split_rows))
    dataset_audit = validate_trials(trials, assignments)
    stimulus_audit = audit_paired_stimuli(trials)
    if not dataset_audit.valid or not stimulus_audit.valid:
        raise ValueError(
            "V0 corpus audit failed: "
            f"dataset={dataset_audit.errors}, stimulus={stimulus_audit.errors}"
        )
    source_paths = (
        Path("scripts/build_v0_paired.py"),
        Path("src/provtrust/datasets/synthetic_builder.py"),
        Path("src/provtrust/datasets/stimulus_audit.py"),
        Path("src/provtrust/datasets/v0_corpus.py"),
        Path("src/provtrust/tasks/common.py"),
    )
    split_counts = Counter(assignment.split for assignment in assignments)
    claim_truth_counts = Counter(str(trial.claim_truth).lower() for trial in trials)
    audit_value = {
        "schema_version": "1.0.0",
        "status": "passed",
        "scope": "v0_paired_synthetic_dataset_identification",
        "scientific_results_present": False,
        "dataset_sha256": dataset_hash,
        "split_sha256": split_hash,
        "config_sha256": sha256_file(args.config),
        "source_code_sha256": {
            _relative(path, root): sha256_file(path) for path in source_paths
        },
        "dataset_audit": dataset_audit.model_dump(mode="json"),
        "stimulus_audit": stimulus_audit.model_dump(mode="json"),
        "split_counts": dict(sorted(split_counts.items())),
        "claim_truth_counts": dict(sorted(claim_truth_counts.items())),
    }
    audit_hash = atomic_write_json(args.audit, audit_value)
    manifest = {
        "schema_version": "1.0.0",
        "dataset_id": spec.dataset_id,
        "purpose": spec.purpose,
        "protocol": "audited_static_v1",
        "builder": "provtrust.datasets.v0_corpus:build_v0_corpus",
        "builder_version": spec.builder_version,
        "seed": spec.seed,
        "path": _relative(args.dataset, root),
        "sha256": dataset_hash,
        "config_path": _relative(args.config, root),
        "config_sha256": sha256_file(args.config),
        "splits_path": _relative(args.splits, root),
        "splits_sha256": split_hash,
        "audit_path": _relative(args.audit, root),
        "audit_sha256": audit_hash,
        "license": spec.license,
        "redistributable": spec.redistributable,
        "contains_fabricated_real_world_claims": spec.contains_real_world_claims,
        "family_count": len(spec.families),
        "item_count": len(trials),
        "variants_per_family": len(trials) // len(spec.families),
        "split_counts": dict(sorted(split_counts.items())),
        "source_code_sha256": audit_value["source_code_sha256"],
    }
    manifest_content = yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True).encode(
        "utf-8"
    )
    manifest_hash = atomic_write_bytes(args.manifest, manifest_content)
    print(
        json.dumps(
            {
                "status": "passed",
                "dataset": str(args.dataset),
                "dataset_sha256": dataset_hash,
                "manifest_sha256": manifest_hash,
                "audit_sha256": audit_hash,
                "families": len(spec.families),
                "items": len(trials),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
