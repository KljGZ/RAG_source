"""Model-free acceptance for the frozen interactive-verification environment."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import yaml

from provtrust.datasets.io import read_jsonl
from provtrust.execution.atomic_io import atomic_write_json, sha256_file
from provtrust.schemas.trial import Trial
from provtrust.tools.canonical_lookup import CanonicalRegistry
from provtrust.tools.controlled_search import ControlledSearchIndex
from provtrust.tools.find_evidence import find_evidence_spans
from provtrust.tools.open_snapshot import SnapshotStore
from provtrust.tools.provenance_trace import ProvenanceRegistry
from provtrust.tools.tool_policy import ToolPolicy
from provtrust.tools.verify_identifier import IdentifierRegistry, IdentifierType


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML object: {path}")
    return value


def _contained_file(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError(f"invalid project-relative file: {relative!r}")
    path = (root / relative).resolve()
    if path == root or root not in path.parents or not path.is_file():
        raise ValueError(f"missing or escaping project file: {relative}")
    return path


def _record(failures: list[str], condition: bool, label: str) -> None:
    if not condition:
        failures.append(label)


def _git_state(root: Path) -> dict[str, Any]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {"revision": revision, "clean": not status.strip()}


def validate_environment(
    *,
    root: Path,
    dataset_manifest_path: Path,
    tool_manifest_path: Path,
    expected_policy: str,
    web_url: str | None = None,
    search_url: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    dataset_manifest = _load_yaml(dataset_manifest_path)
    tool_manifest = _load_yaml(tool_manifest_path)
    failures: list[str] = []

    dataset_path = _contained_file(root, dataset_manifest.get("path"))
    _record(
        failures,
        sha256_file(dataset_path) == dataset_manifest.get("sha256"),
        "dataset_hash_mismatch",
    )
    _record(
        failures,
        dataset_manifest.get("interactive_policy") == expected_policy,
        "dataset_policy_mismatch",
    )
    _record(
        failures,
        dataset_manifest.get("tool_environment_manifest")
        == tool_manifest_path.resolve().relative_to(root).as_posix(),
        "dataset_tool_manifest_path_mismatch",
    )
    _record(
        failures,
        dataset_manifest.get("tool_environment_manifest_sha256")
        == sha256_file(tool_manifest_path),
        "dataset_tool_manifest_hash_mismatch",
    )

    file_entries = tool_manifest.get("files")
    if not isinstance(file_entries, list) or not file_entries:
        raise TypeError("tool manifest requires a nonempty files array")
    observed_paths: set[str] = set()
    for entry in file_entries:
        if not isinstance(entry, dict):
            failures.append("tool_manifest_entry_invalid")
            continue
        relative = entry.get("path")
        try:
            path = _contained_file(root, relative)
        except ValueError:
            failures.append(f"tool_file_invalid:{relative}")
            continue
        if not isinstance(relative, str):
            failures.append("tool_file_path_invalid")
            continue
        _record(failures, relative not in observed_paths, f"tool_file_duplicate:{relative}")
        observed_paths.add(relative)
        _record(
            failures,
            sha256_file(path) == entry.get("sha256"),
            f"tool_file_hash_mismatch:{relative}",
        )
        _record(
            failures,
            path.stat().st_size == entry.get("bytes"),
            f"tool_file_size_mismatch:{relative}",
        )

    search_path = _contained_file(root, tool_manifest.get("search_index_path"))
    source_registry_path = _contained_file(root, tool_manifest.get("source_registry_path"))
    identifier_registry_path = _contained_file(
        root, tool_manifest.get("identifier_registry_path")
    )
    provenance_registry_path = _contained_file(
        root, tool_manifest.get("provenance_registry_path")
    )
    snapshot_manifest_path = _contained_file(
        root, tool_manifest.get("snapshot_manifest_path")
    )
    snapshot_root_value = tool_manifest.get("snapshot_root")
    if not isinstance(snapshot_root_value, str) or Path(snapshot_root_value).is_absolute():
        raise ValueError("tool manifest snapshot_root must be project-relative")
    snapshot_root = (root / snapshot_root_value).resolve()
    if root not in snapshot_root.parents or not snapshot_root.is_dir():
        raise ValueError("snapshot root is missing or escapes the project")

    snapshot_manifest = json.loads(snapshot_manifest_path.read_text(encoding="utf-8"))
    snapshot_entries = snapshot_manifest.get("files")
    if not isinstance(snapshot_entries, list):
        raise TypeError("snapshot manifest requires files")
    expected_snapshots = {
        str(entry["path"])
        for entry in snapshot_entries
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }
    actual_snapshots = {
        path.relative_to(root).as_posix() for path in snapshot_root.glob("*.txt")
    }
    _record(
        failures,
        len(expected_snapshots) == len(snapshot_entries),
        "snapshot_manifest_entries_invalid",
    )
    _record(failures, expected_snapshots == actual_snapshots, "snapshot_membership_mismatch")
    _record(
        failures,
        expected_snapshots <= observed_paths,
        "snapshot_files_not_covered_by_tool_manifest",
    )

    trials = tuple(Trial.model_validate(row) for row in read_jsonl(dataset_path))
    search = ControlledSearchIndex.from_jsonl(search_path)
    source_registry = CanonicalRegistry.from_json(source_registry_path)
    identifiers = IdentifierRegistry.from_json(identifier_registry_path)
    provenance = ProvenanceRegistry.from_json(provenance_registry_path)
    snapshots = SnapshotStore(
        snapshot_root,
        ToolPolicy(allowed_file_roots=(snapshot_root,), max_read_bytes=1_000_000),
        search.documents,
    )
    documents = {document.document_id: document for document in search.documents}

    scenario_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    family_ids: set[str] = set()
    paired: dict[str, set[str]] = defaultdict(set)
    semantic_checks = 0
    for trial in trials:
        metadata = trial.metadata
        scenario = str(metadata["scenario_id"])
        risk = str(metadata["risk_condition"])
        family_ids.add(trial.family_id)
        scenario_counts[scenario] += 1
        risk_counts[risk] += 1
        paired[str(metadata["paired_scene_id"])].add(risk)
        _record(
            failures,
            metadata.get("interactive_policy") == expected_policy,
            f"trial_policy_mismatch:{trial.item_id}",
        )

        source_id = str(metadata["expected_canonical_source_id"])
        canonical_id = str(metadata["expected_canonical_document_id"])
        presented_id = str(metadata["presented_document_id"])
        canonical = documents.get(canonical_id)
        _record(failures, canonical is not None, f"canonical_document_missing:{trial.item_id}")
        if canonical is None:
            continue
        resolved = source_registry.lookup(source_id)
        _record(
            failures,
            any(str(row.get("source_id")) == source_id for row in resolved),
            f"canonical_source_unresolved:{trial.item_id}",
        )
        canonical_hits = search.search(str(canonical.identifier), limit=20)
        _record(
            failures,
            any(hit.document_id == canonical_id for hit in canonical_hits),
            f"canonical_search_failed:{trial.item_id}",
        )
        opened = snapshots.open_document(
            canonical_id, str(metadata["expected_canonical_snapshot_sha256"])
        )
        _record(
            failures,
            opened["sha256"] == metadata["expected_canonical_snapshot_sha256"],
            f"canonical_snapshot_hash_mismatch:{trial.item_id}",
        )
        identifier = str(metadata["presented_identifier"])
        identifier_result = identifiers.verify(identifier, IdentifierType.ANNOUNCEMENT)
        _record(
            failures,
            identifier_result["registry_match"]
            is bool(metadata["presented_identifier_should_match"]),
            f"identifier_semantics_mismatch:{trial.item_id}",
        )
        evidence_text = str(metadata["expected_evidence_text"])
        opened_text = str(opened["text"])
        spans = find_evidence_spans(opened_text, evidence_text)
        _record(
            failures,
            len(spans) == 1
            and spans[0].start == metadata["expected_evidence_span_start"]
            and spans[0].end == metadata["expected_evidence_span_end"],
            f"evidence_span_mismatch:{trial.item_id}",
        )
        page_exists = bool(metadata["page_exists"])
        presented_hits = search.search(identifier, limit=20)
        _record(
            failures,
            any(hit.document_id == presented_id for hit in presented_hits) is page_exists,
            f"presented_search_semantics_mismatch:{trial.item_id}",
        )
        trace = provenance.trace(presented_id)
        _record(
            failures,
            (trace["status"] == "found") is page_exists,
            f"provenance_existence_mismatch:{trial.item_id}",
        )
        if page_exists and metadata.get("requires_temporal_check") is True:
            record = trace.get("record")
            _record(
                failures,
                isinstance(record, dict)
                and isinstance(record.get("published_at"), str)
                and isinstance(record.get("edges"), list),
                f"provenance_temporality_missing:{trial.item_id}",
            )
        semantic_checks += 7

    expected_scenarios = {
        "c1_authentic_direct",
        "c2_authentic_partial",
        "c3_false_attribution",
        "c4_spoofed_identity",
        "c5_missing_reference",
    }
    _record(failures, len(trials) == 160, "unexpected_trial_count")
    _record(failures, len(family_ids) == 16, "unexpected_family_count")
    _record(failures, set(scenario_counts) == expected_scenarios, "scenario_set_mismatch")
    _record(
        failures,
        all(scenario_counts[name] == 32 for name in expected_scenarios),
        "scenario_balance_mismatch",
    )
    _record(failures, risk_counts == {"low": 80, "high": 80}, "risk_balance_mismatch")
    _record(
        failures,
        len(paired) == 80 and all(risks == {"low", "high"} for risks in paired.values()),
        "low_high_pairing_mismatch",
    )
    _record(failures, len(documents) == 81, "unexpected_document_count")

    service_checks: dict[str, Any] = {"required": web_url is not None and search_url is not None}
    if web_url is not None or search_url is not None:
        if web_url is None or search_url is None:
            raise ValueError("web_url and search_url must be supplied together")
        with httpx.Client(timeout=5.0, follow_redirects=False, trust_env=False) as client:
            for name, base in (("controlled-web", web_url), ("controlled-search", search_url)):
                health = client.get(f"{base.rstrip('/')}/healthz")
                health_payload = health.json()
                ok = health.status_code == 200 and health_payload == {
                    "status": "ok",
                    "documents": 81,
                }
                service_checks[f"{name}_health"] = ok
                _record(failures, ok, f"service_health_failed:{name}")
            manifest_response = client.get(f"{web_url.rstrip('/')}/manifest")
            manifest_payload = manifest_response.json()
            manifest_ok = (
                manifest_response.status_code == 200
                and manifest_payload.get("isolated") is True
                and manifest_payload.get("public_indexing_disabled") is True
                and manifest_payload.get("index_sha256") == sha256_file(search_path)
                and len(manifest_payload.get("document_ids", [])) == 81
            )
            service_checks["web_manifest"] = manifest_ok
            _record(failures, manifest_ok, "service_manifest_mismatch")
            first = trials[0]
            canonical_id = str(first.metadata["expected_canonical_document_id"])
            source_response = client.get(
                f"{web_url.rstrip('/')}/source/{quote(canonical_id, safe='')}"
            )
            source_ok = (
                source_response.status_code == 200
                and str(first.metadata["expected_evidence_text"]) in source_response.text
                and source_response.headers.get("cache-control") == "no-store"
                and source_response.headers.get("x-robots-tag", "").startswith("noindex")
            )
            service_checks["canonical_page"] = source_ok
            _record(failures, source_ok, "service_canonical_page_failed")
            search_response = client.get(
                f"{search_url.rstrip('/')}/api/search",
                params={"q": str(first.metadata["presented_identifier"]), "limit": 20},
            )
            search_rows = search_response.json()
            search_ok = search_response.status_code == 200 and any(
                isinstance(row, dict)
                and row.get("document_id") == first.metadata["presented_document_id"]
                for row in search_rows
            )
            service_checks["search_api"] = search_ok
            _record(failures, search_ok, "service_search_api_failed")

    unique_failures = sorted(set(failures))
    validator_path = Path(__file__).resolve()
    return {
        "schema_version": "1.0.0",
        "status": "passed" if not unique_failures else "failed",
        "captured_at": datetime.now(UTC).isoformat(),
        "purpose": "model-free semantic acceptance of interactive_verification_v1",
        "model_calls": 0,
        "gpu_requested": False,
        "repository": _git_state(root),
        "validator": {
            "path": validator_path.relative_to(root).as_posix(),
            "sha256": sha256_file(validator_path),
        },
        "dataset": {
            "manifest_path": dataset_manifest_path.resolve().relative_to(root).as_posix(),
            "manifest_sha256": sha256_file(dataset_manifest_path),
            "path": dataset_path.relative_to(root).as_posix(),
            "sha256": sha256_file(dataset_path),
            "policy": expected_policy,
            "trials": len(trials),
            "families": len(family_ids),
            "paired_scenes": len(paired),
            "scenario_counts": dict(sorted(scenario_counts.items())),
            "risk_counts": dict(sorted(risk_counts.items())),
        },
        "tool_environment": {
            "manifest_path": tool_manifest_path.resolve().relative_to(root).as_posix(),
            "manifest_sha256": sha256_file(tool_manifest_path),
            "environment_version": tool_manifest.get("environment_version"),
            "manifest_file_count": len(file_entries),
            "document_count": len(documents),
            "snapshot_count": len(actual_snapshots),
            "trial_semantic_checks": semantic_checks,
        },
        "services": service_checks,
        "failures": unique_failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=Path("benchmark/manifests/v0-interactive-v1-tools_prompted.yaml"),
    )
    parser.add_argument(
        "--tool-manifest",
        type=Path,
        default=Path("benchmark/manifests/interactive-v1-tools.yaml"),
    )
    parser.add_argument("--expected-policy", default="tools_prompted")
    parser.add_argument("--web-url")
    parser.add_argument("--search-url")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate_environment(
        root=Path.cwd(),
        dataset_manifest_path=args.dataset_manifest,
        tool_manifest_path=args.tool_manifest,
        expected_policy=args.expected_policy,
        web_url=args.web_url,
        search_url=args.search_url,
    )
    artifact_sha256 = atomic_write_json(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": args.output.as_posix(),
                "sha256": artifact_sha256,
                "failures": report["failures"],
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
