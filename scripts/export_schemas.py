"""Export canonical JSON Schema snapshots for all persisted research records."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from provtrust.execution.atomic_io import atomic_write_json
from provtrust.schemas import (
    AttemptRecord,
    Claim,
    Evidence,
    ModelSpec,
    ProvenanceEdge,
    ProvenanceGraph,
    RunManifest,
    SourceEntity,
    ToolEvent,
    Trial,
    TrialResult,
)

SCHEMAS = {
    "attempt-record": AttemptRecord,
    "claim": Claim,
    "evidence": Evidence,
    "model-spec": ModelSpec,
    "provenance-edge": ProvenanceEdge,
    "provenance-graph": ProvenanceGraph,
    "run-manifest": RunManifest,
    "source-entity": SourceEntity,
    "tool-event": ToolEvent,
    "trial": Trial,
    "trial-result": TrialResult,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    for name, model in sorted(SCHEMAS.items()):
        path = output_dir / f"{name}.schema.json"
        payload = model.model_json_schema(mode="validation")
        digest = atomic_write_json(path, payload)
        records.append({"name": name, "path": path.name, "sha256": digest})
    manifest = {
        "schema_version": "1.0.0",
        "generator": "scripts/export_schemas.py",
        "schemas": records,
    }
    content = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    manifest["manifest_content_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    atomic_write_json(output_dir / "MANIFEST.json", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
