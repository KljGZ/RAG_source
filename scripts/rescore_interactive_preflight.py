"""Auditably rescore an immutable interactive preflight under trace definition v2."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from inspect_ai.log import read_eval_log

from provtrust.datasets.io import read_jsonl
from provtrust.execution.atomic_io import atomic_write_json, sha256_file
from provtrust.schemas.trial import Trial
from provtrust.scorers.interactive_trace import interactive_verification_summary

OLD_DEFINITION = "trial_specific_interactive_v1"
NEW_DEFINITION = "trial_specific_interactive_v2"
COMPONENTS = {
    "canonical_source_resolved",
    "canonical_record_found",
    "presented_record_existence_checked",
    "canonical_snapshot_opened",
    "claimed_identifier_checked",
    "canonical_evidence_span_recorded",
    "conflict_temporality_checked",
}
ALLOWED_CHANGED_FIELDS = {"definition", "components", "missing_components", "completed"}


def _as_dict(value: Any, *, label: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python", exclude_none=True)
        if isinstance(dumped, dict):
            return dumped
    raise TypeError(f"{label} is not an object")


def _portable_path(path: Path) -> str:
    resolved = path.resolve()
    root = Path.cwd().resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _definition_hash(manifest: dict[str, Any], path: str) -> str | None:
    files = manifest.get("files")
    if not isinstance(files, list):
        return None
    matches = [
        row.get("sha256") for row in files if isinstance(row, dict) and row.get("path") == path
    ]
    return str(matches[0]) if len(matches) == 1 else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--source-preflight", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--scorer-acceptance", type=Path, required=True)
    parser.add_argument("--amendment", type=Path, required=True)
    parser.add_argument("--expected-policy", required=True)
    parser.add_argument("--expected-raw-log-sha256", required=True)
    parser.add_argument("--expected-source-preflight-sha256", required=True)
    parser.add_argument("--expected-old-scorer-sha256", required=True)
    parser.add_argument("--expected-samples", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_hash = sha256_file(args.source_preflight)
    raw_hash = sha256_file(args.log)
    source = json.loads(args.source_preflight.read_text(encoding="utf-8"))
    dataset_manifest = yaml.safe_load(args.dataset_manifest.read_text(encoding="utf-8"))
    scorer_acceptance = json.loads(args.scorer_acceptance.read_text(encoding="utf-8"))
    if not isinstance(source, dict) or not isinstance(dataset_manifest, dict):
        raise TypeError("source evidence and dataset manifest must be objects")
    if not isinstance(scorer_acceptance, dict):
        raise TypeError("scorer acceptance must be an object")

    dataset_path = Path(str(dataset_manifest["path"]))
    expected_rows = list(read_jsonl(dataset_path))[: args.expected_samples]
    expected_ids = {str(row["item_id"]) for row in expected_rows}
    old_runtime = source.get("runtime_code")
    old_runtime_path = (
        Path(str(old_runtime["manifest_path"]))
        if isinstance(old_runtime, dict) and isinstance(old_runtime.get("manifest_path"), str)
        else None
    )
    old_runtime_manifest = (
        json.loads(old_runtime_path.read_text(encoding="utf-8"))
        if old_runtime_path is not None and old_runtime_path.is_file()
        else {}
    )

    log = read_eval_log(args.log)
    samples = list(log.samples or [])
    rows: list[dict[str, Any]] = []
    observed_ids: list[str] = []
    policies: set[str] = set()
    old_definitions: Counter[str] = Counter()
    new_definitions: Counter[str] = Counter()
    changed_fields_seen: set[str] = set()
    unexpected_component_changes: list[str] = []
    invariants_hold = True
    no_vacuous_absence = True
    old_completed = 0
    new_completed = 0
    old_triggered = 0
    new_triggered = 0
    old_calls = 0
    new_calls = 0
    changed_sample_count = 0
    presented_component_change_count = 0

    for sample in samples:
        sample_id = str(sample.id)
        observed_ids.append(sample_id)
        metadata = _as_dict(sample.metadata, label=f"sample metadata:{sample_id}")
        trial = Trial.model_validate(
            _as_dict(metadata.get("trial"), label=f"trial metadata:{sample_id}")
        )
        policy = str(trial.metadata["interactive_policy"])
        policies.add(policy)
        score = sample.scores.get("structured_parse_scorer") if sample.scores is not None else None
        score_metadata = _as_dict(score.metadata, label=f"score metadata:{sample_id}")
        old_trace = _as_dict(
            score_metadata.get("verification"), label=f"old verification:{sample_id}"
        )
        new_trace = interactive_verification_summary(list(sample.messages), trial)
        old_definition = str(old_trace.get("definition"))
        new_definition = str(new_trace.get("definition"))
        old_definitions[old_definition] += 1
        new_definitions[new_definition] += 1

        changed_fields = sorted(
            key
            for key in set(old_trace) | set(new_trace)
            if old_trace.get(key) != new_trace.get(key)
        )
        changed_fields_seen.update(changed_fields)
        changed_sample_count += int(bool(changed_fields))
        old_components = _as_dict(old_trace.get("components"), label=f"old components:{sample_id}")
        new_components = _as_dict(new_trace.get("components"), label=f"new components:{sample_id}")
        changed_components = sorted(
            key
            for key in set(old_components) | set(new_components)
            if old_components.get(key) != new_components.get(key)
        )
        if set(old_components) != COMPONENTS or set(new_components) != COMPONENTS:
            invariants_hold = False
        if set(changed_components) - {"presented_record_existence_checked"}:
            unexpected_component_changes.append(sample_id)
        presented_component_change_count += int(
            "presented_record_existence_checked" in changed_components
        )
        invariant_fields = (
            "triggered",
            "tool_call_count",
            "successful_tool_call_count",
            "failed_tool_call_count",
            "tool_failure_rate",
            "calls",
        )
        if any(old_trace.get(key) != new_trace.get(key) for key in invariant_fields):
            invariants_hold = False

        page_exists = bool(trial.metadata["page_exists"])
        new_call_rows = new_trace.get("calls")
        successful_searches = (
            sum(
                1
                for call in new_call_rows
                if isinstance(call, dict)
                and call.get("tool_name") == "controlled_search"
                and call.get("succeeded") is True
            )
            if isinstance(new_call_rows, list)
            else 0
        )
        if (
            not page_exists
            and successful_searches == 0
            and new_components["presented_record_existence_checked"] is True
        ):
            no_vacuous_absence = False

        old_completed += int(old_trace.get("completed") is True)
        new_completed += int(new_trace.get("completed") is True)
        old_triggered += int(old_trace.get("triggered") is True)
        new_triggered += int(new_trace.get("triggered") is True)
        old_calls += int(old_trace.get("tool_call_count", 0))
        new_calls += int(new_trace.get("tool_call_count", 0))
        claimed_verified = (
            _as_dict(score_metadata.get("posterior"), label=f"posterior:{sample_id}").get(
                "claimed_verified"
            )
            is True
        )
        rows.append(
            {
                "item_id": sample_id,
                "family_id": trial.family_id,
                "scenario": str(trial.metadata["scenario_id"]),
                "risk": str(trial.metadata["risk_condition"]),
                "policy": policy,
                "page_exists": page_exists,
                "successful_controlled_search_count": successful_searches,
                "changed_fields": changed_fields,
                "changed_components": changed_components,
                "old": {
                    "definition": old_definition,
                    "triggered": old_trace["triggered"],
                    "completed": old_trace["completed"],
                    "components": old_components,
                    "missing_components": old_trace["missing_components"],
                    "tool_call_count": old_trace["tool_call_count"],
                    "false_verification_assurance": score_metadata.get(
                        "false_verification_assurance"
                    ),
                },
                "new": {
                    "definition": new_definition,
                    "triggered": new_trace["triggered"],
                    "completed": new_trace["completed"],
                    "components": new_components,
                    "missing_components": new_trace["missing_components"],
                    "tool_call_count": new_trace["tool_call_count"],
                    "false_verification_assurance": claimed_verified
                    and not bool(new_trace["completed"]),
                },
            }
        )

    source_raw = source.get("raw_log")
    source_observations = source.get("observations")
    source_runtime_hash = (
        str(old_runtime.get("manifest_sha256")) if isinstance(old_runtime, dict) else None
    )
    gates = {
        "source_preflight_hash_matches": source_hash == args.expected_source_preflight_sha256,
        "source_preflight_passed": source.get("status") == "passed",
        "raw_log_hash_matches_expected": raw_hash == args.expected_raw_log_sha256,
        "raw_log_hash_matches_source": isinstance(source_raw, dict)
        and source_raw.get("sha256") == raw_hash,
        "raw_log_size_matches_source": isinstance(source_raw, dict)
        and source_raw.get("bytes") == args.log.stat().st_size,
        "raw_log_eval_succeeded": log.status == "success" and log.invalidated is False,
        "exact_sample_count": len(samples) == args.expected_samples,
        "no_duplicate_sample_ids": len(observed_ids) == len(set(observed_ids)),
        "exact_frozen_sample_ids": set(observed_ids) == expected_ids,
        "exact_policy": policies == {args.expected_policy},
        "old_definition_is_v1": old_definitions == {OLD_DEFINITION: args.expected_samples},
        "new_definition_is_v2": new_definitions == {NEW_DEFINITION: args.expected_samples},
        "old_scorer_hash_is_frozen": _definition_hash(
            old_runtime_manifest, "src/provtrust/scorers/interactive_trace.py"
        )
        == args.expected_old_scorer_sha256,
        "old_runtime_manifest_hash_matches_source": old_runtime_path is not None
        and source_runtime_hash == sha256_file(old_runtime_path),
        "scorer_acceptance_passed": scorer_acceptance.get("status") == "passed",
        "scorer_acceptance_definition_is_v2": scorer_acceptance.get("definition") == NEW_DEFINITION,
        "scorer_acceptance_binds_current_code": isinstance(scorer_acceptance.get("scorer"), dict)
        and scorer_acceptance["scorer"].get("sha256")
        == sha256_file(Path("src/provtrust/scorers/interactive_trace.py")),
        "only_authorized_trace_fields_changed": changed_fields_seen <= ALLOWED_CHANGED_FIELDS,
        "only_presented_component_changed": not unexpected_component_changes,
        "trace_invariants_hold": invariants_hold,
        "trigger_count_unchanged": old_triggered == new_triggered,
        "tool_call_count_unchanged": old_calls == new_calls,
        "no_vacuous_absence_passes": no_vacuous_absence,
        "old_aggregate_matches_source": isinstance(source_observations, dict)
        and source_observations.get("completed_count") == old_completed
        and source_observations.get("triggered_count") == old_triggered
        and source_observations.get("tool_call_count") == old_calls,
        "no_sample_errors": all(sample.error is None for sample in samples),
    }
    failures = sorted(name for name, passed in gates.items() if not passed)
    scorer_path = Path("src/provtrust/scorers/interactive_trace.py")
    validator_path = Path(__file__).resolve()
    root = Path.cwd().resolve()
    report = {
        "schema_version": "1.0.0",
        "status": "passed" if not failures else "failed",
        "run_kind": "preflight_rescore",
        "scientific_claims_allowed": False,
        "policy": args.expected_policy,
        "model_asset": source.get("model_asset"),
        "source_preflight": {
            "path": _portable_path(args.source_preflight),
            "sha256": source_hash,
            "plan_sha256": source.get("plan_sha256"),
            "git_revision": (
                source.get("model", {}).get("revision")
                if isinstance(source.get("model"), dict)
                else None
            ),
        },
        "raw_log": {
            "path": _portable_path(args.log),
            "sha256": raw_hash,
            "bytes": args.log.stat().st_size,
            "immutable": True,
        },
        "scorer": {
            "path": scorer_path.as_posix(),
            "sha256": sha256_file(scorer_path),
            "old_definition": OLD_DEFINITION,
            "new_definition": NEW_DEFINITION,
            "old_sha256": args.expected_old_scorer_sha256,
        },
        "scorer_acceptance": {
            "path": _portable_path(args.scorer_acceptance),
            "sha256": sha256_file(args.scorer_acceptance),
        },
        "amendment": {
            "path": _portable_path(args.amendment),
            "sha256": sha256_file(args.amendment),
        },
        "rescore": {
            "definition": NEW_DEFINITION,
            "no_new_model_output": True,
            "sample_count": len(samples),
            "changed_sample_count": changed_sample_count,
            "presented_component_change_count": presented_component_change_count,
            "old_completed_count": old_completed,
            "new_completed_count": new_completed,
            "old_triggered_count": old_triggered,
            "new_triggered_count": new_triggered,
            "old_tool_call_count": old_calls,
            "new_tool_call_count": new_calls,
        },
        "acceptance": {"gates": gates, "failures": failures},
        "samples": sorted(rows, key=lambda row: str(row["item_id"])),
        "validator": {
            "path": validator_path.relative_to(root).as_posix(),
            "sha256": sha256_file(validator_path),
        },
        "interpretation_boundary": (
            "This artifact re-evaluates engineering-preflight observability only. It "
            "does not create model output and is excluded from formal V0 estimates."
        ),
    }
    artifact_hash = atomic_write_json(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": args.output.as_posix(),
                "sha256": artifact_hash,
                "rescore": report["rescore"],
                "failures": failures,
            },
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
