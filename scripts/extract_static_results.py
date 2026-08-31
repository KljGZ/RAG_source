"""Extract and summarize frozen static-factorial Inspect logs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

import yaml
from inspect_ai.log import read_eval_log

from provtrust.analysis.bootstrap import cluster_bootstrap_mean
from provtrust.analysis.randomization_test import sign_flip_randomization_test
from provtrust.analysis.static_results import StaticObservation, compute_static_contrasts
from provtrust.datasets.io import read_jsonl
from provtrust.execution.atomic_io import atomic_write_bytes, atomic_write_json, sha256_file
from provtrust.scorers.source_sensitivity import normative_factor_control_ratio


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        + b"\n"
        for row in rows
    )


def _holm(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=lambda key: (p_values[key], key))
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for index, key in enumerate(ordered):
        running = max(running, min(1.0, (total - index) * p_values[key]))
        adjusted[key] = running
    return adjusted


def _observation(sample: Any, *, model_id: str) -> StaticObservation:
    if not isinstance(sample.metadata, dict):
        raise TypeError(f"sample metadata is not an object: {sample.id}")
    trial = sample.metadata.get("trial")
    if not isinstance(trial, dict):
        raise TypeError(f"trial metadata missing: {sample.id}")
    trial_metadata = trial.get("metadata")
    factors = trial.get("intervention_vector")
    if not isinstance(trial_metadata, dict) or not isinstance(factors, dict):
        raise TypeError(f"paired design metadata missing: {sample.id}")
    score = sample.scores.get("structured_parse_scorer")
    if score is None or not isinstance(score.metadata, dict):
        raise TypeError(f"structured score metadata missing: {sample.id}")
    metadata = score.metadata
    prior = metadata.get("prior")
    posterior = metadata.get("posterior")
    verification = metadata.get("verification")
    if not isinstance(prior, dict) or not isinstance(posterior, dict):
        raise TypeError(f"structured prior/posterior missing: {sample.id}")
    if not isinstance(verification, dict):
        raise TypeError(f"verification metadata missing: {sample.id}")
    usages = list(sample.model_usage.values())
    if len(usages) != 1:
        raise ValueError(f"expected one model-usage record: {sample.id}")
    usage = usages[0]
    return StaticObservation(
        item_id=str(sample.id),
        family_id=str(trial["claim"]["family_id"]),
        model_id=model_id,
        design_cell_id=str(trial_metadata["design_cell_id"]),
        contrast_factor=(
            str(trial_metadata["contrast_factor"])
            if trial_metadata.get("contrast_factor") is not None
            else None
        ),
        control_cell_id=(
            str(trial_metadata["control_cell_id"])
            if trial_metadata.get("control_cell_id") is not None
            else None
        ),
        claim_truth=trial.get("claim_truth"),
        gold_answer=trial["gold_answer"],
        candidate_answer=trial["candidate_answer"],
        factors=factors,
        parse_success=bool(metadata.get("parse_success")),
        prior_answer=prior.get("answer"),
        prior_confidence=float(prior["confidence"]),
        prior_abstained=bool(prior["abstained"]),
        prior_answer_type_valid=bool(metadata.get("prior_answer_type_valid")),
        posterior_answer=posterior.get("answer"),
        posterior_confidence=float(posterior["confidence"]),
        posterior_abstained=bool(posterior["abstained"]),
        posterior_answer_type_valid=bool(metadata.get("posterior_answer_type_valid")),
        claim_adoption_shift=(
            float(metadata["claim_adoption_shift"])
            if metadata.get("claim_adoption_shift") is not None
            else None
        ),
        correct=bool(metadata.get("correct")),
        citation_valid=bool(metadata.get("citation_valid")),
        claimed_verified=bool(posterior.get("claimed_verified")),
        verification_completed=bool(verification.get("completed")),
        false_verification_assurance=bool(metadata.get("false_verification_assurance")),
        input_tokens=int(usage.input_tokens),
        output_tokens=int(usage.output_tokens),
        total_tokens=int(usage.total_tokens),
        total_time_seconds=float(sample.total_time),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=Path("benchmark/manifests/v0-paired-v1.yaml"),
    )
    parser.add_argument("--expected-model", default="hf/Qwen/Qwen3-14B")
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = yaml.safe_load(args.dataset_manifest.read_text(encoding="utf-8"))
    dataset_path = Path(manifest["path"])
    if sha256_file(dataset_path) != manifest["sha256"]:
        raise ValueError("dataset no longer matches its frozen manifest")
    expected_ids = {str(row["item_id"]) for row in read_jsonl(dataset_path)}
    observations: list[StaticObservation] = []
    raw_logs: list[dict[str, Any]] = []
    revisions: set[str] = set()
    for path in args.logs:
        log = read_eval_log(path)
        if log.status != "success":
            raise ValueError(f"eval log is not successful: {path}")
        if log.eval.model != args.expected_model:
            raise ValueError(f"unexpected model in eval log: {log.eval.model}")
        metadata = log.eval.metadata or {}
        if metadata.get("provtrust_plan_sha256") != args.expected_plan_sha256:
            raise ValueError(f"plan hash mismatch in eval log: {path}")
        if log.eval.revision is None or log.eval.revision.dirty:
            raise ValueError(f"eval log lacks a clean Git revision: {path}")
        revisions.add(log.eval.revision.commit)
        if log.samples is None:
            raise ValueError(f"eval log has no samples: {path}")
        observations.extend(
            _observation(sample, model_id=args.expected_model) for sample in log.samples
        )
        raw_logs.append(
            {
                "path": path.as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "eval_id": log.eval.eval_id,
                "run_id": log.eval.run_id,
                "task_id": log.eval.task_id,
                "started_at": log.stats.started_at,
                "completed_at": log.stats.completed_at,
            }
        )
    observed_ids = {observation.item_id for observation in observations}
    if len(observed_ids) != len(observations):
        raise ValueError("eval logs contain duplicate sample identifiers")
    if observed_ids != expected_ids:
        raise ValueError(
            f"eval coverage mismatch: missing={len(expected_ids - observed_ids)}, "
            f"unexpected={len(observed_ids - expected_ids)}"
        )
    if len(revisions) != 1:
        raise ValueError("eval logs span multiple Git revisions")
    if not all(observation.parse_success for observation in observations):
        raise ValueError("one or more samples failed structured parsing")
    effects = compute_static_contrasts(tuple(observations))
    by_contrast: dict[str, list[float]] = defaultdict(list)
    contrast_metadata: dict[str, tuple[str, str]] = {}
    for effect in effects:
        by_contrast[effect.contrast_id].append(effect.raw_adoption_effect)
        contrast_metadata[effect.contrast_id] = (effect.factor, effect.factor_class)
    aggregate_rows: list[dict[str, Any]] = []
    p_values: dict[str, float] = {}
    for index, contrast_id in enumerate(sorted(by_contrast)):
        values = tuple(by_contrast[contrast_id])
        bootstrap = cluster_bootstrap_mean(
            {str(i): (value,) for i, value in enumerate(values)},
            seed=args.seed + index,
        )
        randomization = sign_flip_randomization_test(values, seed=args.seed + index)
        p_values[contrast_id] = randomization.p_value_two_sided
        factor, factor_class = contrast_metadata[contrast_id]
        aggregate_rows.append(
            {
                "contrast_id": contrast_id,
                "factor": factor,
                "factor_class": factor_class,
                "family_count": len(values),
                "raw_effect_mean": bootstrap.estimate,
                "raw_effect_median": median(values),
                "ci95_lower": bootstrap.lower,
                "ci95_upper": bootstrap.upper,
                "bootstrap_replicates": bootstrap.replicates,
                "randomization_p_two_sided": randomization.p_value_two_sided,
                "randomization_exact": randomization.exact,
                "randomization_permutations": randomization.permutations,
            }
        )
    adjusted = _holm(p_values)
    for row in aggregate_rows:
        row["holm_adjusted_p"] = adjusted[str(row["contrast_id"])]
    normative = [
        abs(float(row["raw_effect_mean"]))
        for row in aggregate_rows
        if row["factor_class"] == "normative"
    ]
    heuristic = [
        abs(float(row["raw_effect_mean"]))
        for row in aggregate_rows
        if row["factor_class"] == "heuristic"
    ]
    output = args.output_dir
    observation_hash = atomic_write_bytes(
        output / "observations.jsonl",
        _jsonl([value.model_dump(mode="json") for value in observations]),
    )
    effects_hash = atomic_write_bytes(
        output / "paired_effects.jsonl",
        _jsonl([value.model_dump(mode="json") for value in effects]),
    )
    parse_count = sum(value.parse_success for value in observations)
    summary = {
        "schema_version": "1.0.0",
        "status": "complete",
        "scope": "exploratory_single_model_closed_world_synthetic_v0",
        "confirmatory": False,
        "model": args.expected_model,
        "git_revision": next(iter(revisions)),
        "dataset_manifest_sha256": sha256_file(args.dataset_manifest),
        "dataset_sha256": manifest["sha256"],
        "plan_sha256": args.expected_plan_sha256,
        "sample_count": len(observations),
        "family_count": len({value.family_id for value in observations}),
        "parse_success_count": parse_count,
        "parse_success_rate": parse_count / len(observations),
        "posterior_answer_type_valid_rate": sum(
            value.posterior_answer_type_valid for value in observations
        )
        / len(observations),
        "accuracy": sum(value.correct for value in observations) / len(observations),
        "posterior_abstention_rate": sum(value.posterior_abstained for value in observations)
        / len(observations),
        "false_verification_assurance_rate": sum(
            value.false_verification_assurance for value in observations
        )
        / len(observations),
        "citation_valid_rate": sum(value.citation_valid for value in observations)
        / len(observations),
        "total_tokens": sum(value.total_tokens for value in observations),
        "total_sample_seconds": sum(value.total_time_seconds for value in observations),
        "normative_factor_control_ratio": normative_factor_control_ratio(
            tuple(normative), tuple(heuristic)
        ),
        "contrasts": aggregate_rows,
        "interpretation_boundary": (
            "Exploratory effects from one open-weight model and a closed-world synthetic "
            "corpus; they do not establish general SDI/PGSD claims or confirmatory evidence."
        ),
    }
    summary_hash = atomic_write_json(output / "summary.json", summary)
    run_manifest = {
        "schema_version": "1.0.0",
        "status": "complete",
        "raw_logs": raw_logs,
        "observations": {
            "path": "observations.jsonl",
            "sha256": observation_hash,
            "count": len(observations),
        },
        "paired_effects": {
            "path": "paired_effects.jsonl",
            "sha256": effects_hash,
            "count": len(effects),
        },
        "summary": {"path": "summary.json", "sha256": summary_hash},
    }
    manifest_hash = atomic_write_json(output / "MANIFEST.json", run_manifest)
    print(
        json.dumps(
            {
                "status": "complete",
                "output_dir": str(output),
                "manifest_sha256": manifest_hash,
                "samples": len(observations),
                "contrasts": len(effects),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
