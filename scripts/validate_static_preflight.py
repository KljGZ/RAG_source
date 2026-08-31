"""Validate and freeze a deterministic static-factorial preflight run."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from inspect_ai.log import read_eval_log

from provtrust.datasets.io import read_jsonl
from provtrust.execution.atomic_io import atomic_write_json, sha256_file


def _as_dict(value: Any, *, label: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python", exclude_none=True)
        if isinstance(dumped, dict):
            return dumped
    raise TypeError(f"{label} is not an object")


def _retry_count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, (list, tuple)):
        return len(value)
    raise TypeError("unsupported error_retries representation")


def _duration_seconds(started_at: str, completed_at: str) -> float:
    return (
        datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)
    ).total_seconds()


def _portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def _expected_rows(
    manifest: dict[str, Any], expected_samples: int
) -> tuple[list[dict[str, Any]], Path]:
    dataset_path = Path(str(manifest["path"]))
    rows = list(read_jsonl(dataset_path))
    if len(rows) < expected_samples:
        raise ValueError("frozen dataset is smaller than the requested preflight")
    return rows[:expected_samples], dataset_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--model-registration", type=Path, required=True)
    parser.add_argument("--model-asset-manifest", type=Path, required=True)
    parser.add_argument("--expected-model", required=True)
    parser.add_argument("--expected-model-root-sha256", required=True)
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--expected-samples", type=int, default=15)
    parser.add_argument("--expected-families", type=int, default=1)
    parser.add_argument("--expected-model-calls", type=int, default=30)
    parser.add_argument("--expected-seed", type=int, default=20260831)
    parser.add_argument("--run-kind", choices=("preflight", "exploratory_v0"), default="preflight")
    parser.add_argument("--expected-git-revision")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = yaml.safe_load(args.dataset_manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise TypeError("dataset manifest must contain an object")
    expected_rows, dataset_path = _expected_rows(manifest, args.expected_samples)
    dataset_hash_matches = sha256_file(dataset_path) == manifest.get("sha256")
    expected_by_id = {str(row["item_id"]): row for row in expected_rows}
    if len(expected_by_id) != args.expected_samples:
        raise ValueError("preflight reference rows contain duplicate item identifiers")

    asset_manifest = json.loads(args.model_asset_manifest.read_text(encoding="utf-8"))
    if not isinstance(asset_manifest, dict):
        raise TypeError("model asset manifest must contain an object")

    log = read_eval_log(args.log)
    eval_metadata = dict(log.eval.metadata or {})
    generate_config = _as_dict(log.eval.model_generate_config, label="model_generate_config")
    model_args = dict(log.eval.model_args or {})
    samples = list(log.samples or [])

    sample_rows: list[dict[str, Any]] = []
    observed_ids: list[str] = []
    observed_families: set[str] = set()
    observed_cells: set[str] = set()
    parse_success_count = 0
    prior_type_valid_count = 0
    posterior_type_valid_count = 0
    citation_valid_count = 0
    claimed_verified_count = 0
    verification_completed_count = 0
    false_assurance_count = 0
    correct_count = 0
    abstained_count = 0
    retry_count = 0
    sample_error_count = 0
    turn_count = 0
    sample_input_tokens = 0
    sample_output_tokens = 0
    sample_total_tokens = 0
    max_sample_output_tokens = 0
    sample_seconds = 0.0

    for sample in samples:
        sample_id = str(sample.id)
        observed_ids.append(sample_id)
        trial = _as_dict(sample.metadata, label=f"sample metadata: {sample_id}").get("trial")
        trial_dict = _as_dict(trial, label=f"trial metadata: {sample_id}")
        claim = _as_dict(trial_dict.get("claim"), label=f"claim metadata: {sample_id}")
        design = _as_dict(trial_dict.get("metadata"), label=f"design metadata: {sample_id}")
        family_id = str(claim["family_id"])
        cell_id = str(design["design_cell_id"])
        observed_families.add(family_id)
        observed_cells.add(cell_id)

        scores = sample.scores
        if scores is None:
            raise TypeError(f"sample scores missing: {sample_id}")
        score = scores.get("structured_parse_scorer")
        if score is None:
            raise TypeError(f"structured score missing: {sample_id}")
        score_metadata = _as_dict(score.metadata, label=f"score metadata: {sample_id}")
        _as_dict(score_metadata.get("prior"), label=f"prior: {sample_id}")
        posterior = _as_dict(score_metadata.get("posterior"), label=f"posterior: {sample_id}")
        verification = _as_dict(
            score_metadata.get("verification"), label=f"verification: {sample_id}"
        )

        parse_success = score_metadata.get("parse_success") is True
        prior_type_valid = score_metadata.get("prior_answer_type_valid") is True
        posterior_type_valid = score_metadata.get("posterior_answer_type_valid") is True
        citation_valid = score_metadata.get("citation_valid") is True
        claimed_verified = posterior.get("claimed_verified") is True
        verification_completed = verification.get("completed") is True
        false_assurance = score_metadata.get("false_verification_assurance") is True
        correct = score_metadata.get("correct") is True
        abstained = posterior.get("abstained") is True
        parse_success_count += int(parse_success)
        prior_type_valid_count += int(prior_type_valid)
        posterior_type_valid_count += int(posterior_type_valid)
        citation_valid_count += int(citation_valid)
        claimed_verified_count += int(claimed_verified)
        verification_completed_count += int(verification_completed)
        false_assurance_count += int(false_assurance)
        correct_count += int(correct)
        abstained_count += int(abstained)
        retry_count += _retry_count(sample.error_retries)
        sample_error_count += int(sample.error is not None)
        sample_turn_count = sample.turn_count
        sample_total_time = sample.total_time
        if sample_turn_count is None or sample_total_time is None:
            raise TypeError(f"sample timing metadata missing: {sample_id}")
        turn_count += sample_turn_count
        sample_seconds += sample_total_time

        usages = list(sample.model_usage.values())
        if len(usages) != 1:
            raise ValueError(f"expected one model usage record: {sample_id}")
        usage = usages[0]
        sample_input_tokens += int(usage.input_tokens)
        sample_output_tokens += int(usage.output_tokens)
        sample_total_tokens += int(usage.total_tokens)
        max_sample_output_tokens = max(max_sample_output_tokens, int(usage.output_tokens))

        expected = expected_by_id.get(sample_id)
        expected_design = expected.get("metadata") if expected is not None else None
        expected_cell = (
            str(expected_design.get("design_cell_id"))
            if isinstance(expected_design, dict)
            else None
        )
        sample_rows.append(
            {
                "item_id": sample_id,
                "family_id": family_id,
                "design_cell_id": cell_id,
                "expected_design_cell_id": expected_cell,
                "contrast_factor": design.get("contrast_factor"),
                "control_cell_id": design.get("control_cell_id"),
                "parse_success": parse_success,
                "prior_answer_type_valid": prior_type_valid,
                "posterior_answer_type_valid": posterior_type_valid,
                "citation_valid": citation_valid,
                "claimed_verified": claimed_verified,
                "verification_completed": verification_completed,
                "false_verification_assurance": false_assurance,
                "correct": correct,
                "posterior_abstained": abstained,
                "error_retries": _retry_count(sample.error_retries),
                "turn_count": sample_turn_count,
                "total_tokens": int(usage.total_tokens),
            }
        )

    usage_values = list(log.stats.model_usage.values())
    if len(usage_values) != 1:
        raise ValueError("expected one aggregate model usage record")
    aggregate_usage = usage_values[0]
    aggregate_tokens = {
        "input": int(aggregate_usage.input_tokens),
        "output": int(aggregate_usage.output_tokens),
        "total": int(aggregate_usage.total_tokens),
    }

    expected_ids = set(expected_by_id)
    actual_ids = set(observed_ids)
    expected_cells = {
        str(_as_dict(row["metadata"], label="dataset design metadata")["design_cell_id"])
        for row in expected_rows
    }
    exact_cell_mapping = all(
        row["expected_design_cell_id"] == row["design_cell_id"] for row in sample_rows
    )
    revision = log.eval.revision
    results = log.results
    temperature = generate_config.get("temperature")
    gates = {
        "eval_status_success": log.status == "success",
        "eval_not_invalidated": log.invalidated is False,
        "clean_git_revision": revision is not None and revision.dirty is False,
        "expected_git_revision": args.expected_git_revision is None
        or (revision is not None and revision.commit == args.expected_git_revision),
        "expected_model": log.eval.model == args.expected_model,
        "expected_plan_hash": eval_metadata.get("provtrust_plan_sha256")
        == args.expected_plan_sha256,
        "expected_model_root_hash": eval_metadata.get("provtrust_model_root_sha256")
        == args.expected_model_root_sha256,
        "asset_manifest_root_hash": asset_manifest.get("root_sha256")
        == args.expected_model_root_sha256,
        "dataset_hash_matches_manifest": dataset_hash_matches,
        "exact_sample_count": len(samples) == args.expected_samples,
        "exact_completed_sample_count": results is not None
        and results.completed_samples == args.expected_samples,
        "no_duplicate_sample_ids": len(observed_ids) == len(actual_ids),
        "exact_frozen_sample_ids": actual_ids == expected_ids,
        "exact_design_cell_mapping": exact_cell_mapping,
        "exact_design_cells": observed_cells == expected_cells,
        "exact_family_count": len(observed_families) == args.expected_families,
        "all_structured_outputs_parse": parse_success_count == args.expected_samples,
        "all_prior_answer_types_valid": prior_type_valid_count == args.expected_samples,
        "all_posterior_answer_types_valid": posterior_type_valid_count == args.expected_samples,
        "all_citations_reference_supplied_evidence": citation_valid_count == args.expected_samples,
        "no_completed_verification_without_tools": verification_completed_count == 0,
        "no_sample_errors": sample_error_count == 0,
        "no_error_retries": retry_count == 0,
        "exact_model_call_count": turn_count == args.expected_model_calls,
        "token_usage_reconciles": sample_input_tokens == aggregate_tokens["input"]
        and sample_output_tokens == aggregate_tokens["output"]
        and sample_total_tokens == aggregate_tokens["total"],
        "deterministic_temperature": temperature is None or float(temperature) == 0.0,
        "deterministic_seed": int(generate_config.get("seed", -1)) == args.expected_seed,
        "single_connection": int(generate_config.get("max_connections", -1)) == 1,
        "sampling_disabled": model_args.get("do_sample") is False,
        "thinking_disabled": model_args.get("enable_thinking") is False,
        "offline_model_loading": model_args.get("local_files_only") is True,
        "physical_gpu_2_mapped_to_logical_cuda_0": model_args.get("device") == "cuda:0",
    }
    failures = sorted(name for name, passed in gates.items() if not passed)
    status = "passed" if not failures else "failed"
    started_at = str(log.stats.started_at)
    completed_at = str(log.stats.completed_at)
    is_preflight = args.run_kind == "preflight"
    purpose = (
        "deterministic one-family runtime acceptance for audited_static_v1"
        if is_preflight
        else "exploratory 16-family V0 runtime acceptance for audited_static_v1"
    )
    interpretation_boundary = (
        "This preflight validates execution and observability only. Accuracy and false "
        "verification assurance are descriptive observations and were not activation gates."
        if is_preflight
        else "This acceptance validates execution integrity, not a general or confirmatory "
        "SDI/PGSD claim. Scientific interpretation remains limited to one open-weight model "
        "and a closed-world synthetic corpus."
    )
    warnings = (
        [
            (
                "Transformers reported temperature/top-k generation flags as ignored while "
                "do_sample=false. Deterministic decoding was active; the full-run command "
                "omits these redundant CLI flags."
            ),
            (
                "The legacy Inspect headline scorer value is answer correctness despite the "
                "structured_parse_scorer name. Parse acceptance is computed from each score's "
                "parse_success metadata, not from the headline mean."
            ),
        ]
        if is_preflight
        else [
            (
                "Inspect's Hugging Face adapter reported default temperature/top-p/top-k flags "
                "as ignored even though the full-run CLI omitted them. The frozen runtime used "
                "do_sample=false, disabled thinking, a fixed seed, and one connection."
            ),
            (
                "The legacy Inspect headline scorer value is answer correctness despite the "
                "structured_parse_scorer name. Parse acceptance is computed from each score's "
                "parse_success metadata, not from the headline mean."
            ),
            (
                "An unrelated pre-existing GPU process shared physical GPU 2. Memory headroom "
                "remained above 55 GiB and no error or retry occurred; throughput is therefore "
                "not treated as an isolated performance benchmark."
            ),
        ]
    )
    report = {
        "schema_version": "1.0.0",
        "status": status,
        "run_kind": args.run_kind,
        "scientific_claims_allowed": not is_preflight,
        "confirmatory": False,
        "purpose": purpose,
        "interpretation_boundary": interpretation_boundary,
        "model": {
            "inspect_id": args.expected_model,
            "registration_path": args.model_registration.as_posix(),
            "registration_sha256": sha256_file(args.model_registration),
            "revision": revision.commit if revision is not None else None,
            "revision_dirty": revision.dirty if revision is not None else None,
            "generate_config": generate_config,
            "runtime_args": {
                key: model_args.get(key)
                for key in (
                    "device",
                    "dtype",
                    "local_files_only",
                    "trust_remote_code",
                    "low_cpu_mem_usage",
                    "enable_thinking",
                    "do_sample",
                    "batch_size",
                )
            },
        },
        "model_asset": {
            "manifest_path": args.model_asset_manifest.as_posix(),
            "manifest_sha256": sha256_file(args.model_asset_manifest),
            "root_sha256": asset_manifest.get("root_sha256"),
            "file_count": asset_manifest.get("file_count"),
            "total_bytes": asset_manifest.get("total_bytes"),
        },
        "dataset": {
            "manifest_path": args.dataset_manifest.as_posix(),
            "manifest_sha256": sha256_file(args.dataset_manifest),
            "path": dataset_path.as_posix(),
            "sha256": sha256_file(dataset_path),
            "protocol": manifest.get("protocol"),
            "expected_item_ids": sorted(expected_ids),
            "expected_design_cells": sorted(expected_cells),
        },
        "plan_sha256": args.expected_plan_sha256,
        "raw_log": {
            "path": _portable_path(args.log),
            "sha256": sha256_file(args.log),
            "bytes": args.log.stat().st_size,
            "eval_id": log.eval.eval_id,
            "run_id": log.eval.run_id,
            "task_id": log.eval.task_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "wall_time_seconds": _duration_seconds(started_at, completed_at),
        },
        "acceptance": {
            "gates": gates,
            "failures": failures,
            "expected_samples": args.expected_samples,
            "expected_families": args.expected_families,
            "expected_model_calls": args.expected_model_calls,
        },
        "observations": {
            "sample_count": len(samples),
            "family_count": len(observed_families),
            "design_cell_count": len(observed_cells),
            "parse_success_count": parse_success_count,
            "prior_answer_type_valid_count": prior_type_valid_count,
            "posterior_answer_type_valid_count": posterior_type_valid_count,
            "citation_valid_count": citation_valid_count,
            "claimed_verified_count": claimed_verified_count,
            "verification_completed_count": verification_completed_count,
            "false_verification_assurance_count": false_assurance_count,
            "correct_count": correct_count,
            "posterior_abstained_count": abstained_count,
            "sample_error_count": sample_error_count,
            "error_retry_count": retry_count,
            "model_call_count": turn_count,
            "aggregate_tokens": aggregate_tokens,
            "max_sample_output_tokens": max_sample_output_tokens,
            "summed_sample_seconds": round(sample_seconds, 6),
        },
        "samples": sorted(sample_rows, key=lambda row: str(row["design_cell_id"])),
        "warnings": warnings,
    }
    artifact_sha256 = atomic_write_json(args.output, report)
    print(
        json.dumps(
            {
                "status": status,
                "output": args.output.as_posix(),
                "sha256": artifact_sha256,
                "failures": failures,
            },
            indent=2,
        )
    )
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
