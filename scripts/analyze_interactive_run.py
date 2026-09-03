"""Integrity-check and analyze one frozen 160-row Track E policy run."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from inspect_ai.log import read_eval_log

from provtrust.analysis.interactive_results import (
    InteractiveObservation,
    paired_contrast,
    wilson_rate,
)
from provtrust.datasets.io import read_jsonl
from provtrust.execution.atomic_io import atomic_write_bytes, atomic_write_json, sha256_file
from provtrust.schemas.trial import Trial
from provtrust.scorers.interactive_trace import interactive_verification_summary

SCENARIOS = {
    "c1_authentic_direct",
    "c2_authentic_partial",
    "c3_false_attribution",
    "c4_spoofed_identity",
    "c5_missing_reference",
}
COMPONENTS = {
    "canonical_source_resolved",
    "canonical_record_found",
    "presented_record_existence_checked",
    "canonical_snapshot_opened",
    "claimed_identifier_checked",
    "canonical_evidence_span_recorded",
    "conflict_temporality_checked",
}


def _as_dict(value: Any, *, label: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python", exclude_none=True)
        if isinstance(dumped, dict):
            return dumped
    raise TypeError(f"{label} is not an object")


def _optional_dict(value: Any) -> dict[str, Any]:
    try:
        return _as_dict(value, label="optional metadata")
    except TypeError:
        return {}


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


def _project_file(value: Any) -> Path | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None
    root = Path.cwd().resolve()
    resolved = (root / value).resolve()
    if resolved == root or root not in resolved.parents or not resolved.is_file():
        return None
    return resolved


def _revision_matches(observed: str | None, expected: str | None) -> bool:
    if expected is None:
        return True
    if observed is None or len(observed) < 7 or len(expected) < 7:
        return False
    return observed.startswith(expected) or expected.startswith(observed)


def _trace_is_redacted(verification: dict[str, Any]) -> bool:
    calls = verification.get("calls")
    if not isinstance(calls, list):
        return False
    for call in calls:
        if not isinstance(call, dict):
            return False
        arguments = call.get("arguments")
        if not isinstance(arguments, dict):
            return False
        document = arguments.get("document")
        if document is not None and not (
            isinstance(document, dict)
            and isinstance(document.get("sha256"), str)
            and isinstance(document.get("characters"), int)
        ):
            return False
        if not isinstance(call.get("output_sha256"), str):
            return False
    return True


def _runtime_manifest_files_match(manifest: dict[str, Any]) -> bool:
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return False
    paths: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            return False
        path = _project_file(entry.get("path"))
        relative = entry.get("path")
        if path is None or not isinstance(relative, str) or relative in paths:
            return False
        paths.add(relative)
        if entry.get("sha256") != sha256_file(path):
            return False
        if entry.get("bytes") != path.stat().st_size:
            return False
    return manifest.get("entrypoint") in paths


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\n"
        for row in rows
    )


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _answer_or_none(value: Any) -> bool | str | float | None:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _component_rates(
    observations: list[InteractiveObservation],
) -> dict[str, dict[str, float | int | None]]:
    return {
        component: wilson_rate(
            [observation.verification_components[component] for observation in observations]
        )
        for component in sorted(COMPONENTS)
    }


def _numeric_summary(values: list[float | None]) -> dict[str, float | int | None]:
    observed = [value for value in values if value is not None]
    return {
        "denominator": len(observed),
        "missing": len(values) - len(observed),
        "mean": sum(observed) / len(observed) if observed else None,
        "minimum": min(observed) if observed else None,
        "maximum": max(observed) if observed else None,
    }


def _rates(observations: list[InteractiveObservation]) -> dict[str, Any]:
    triggered = [observation.triggered for observation in observations]
    triggered_observations = [observation for observation in observations if observation.triggered]
    total_calls = sum(observation.tool_call_count for observation in observations)
    failed_calls = sum(observation.failed_tool_call_count for observation in observations)
    return {
        "sample_count": len(observations),
        "parse_success": wilson_rate([observation.parse_success for observation in observations]),
        "verification_trigger": wilson_rate(triggered),
        "strict_verification_completion": wilson_rate(
            [observation.completed for observation in observations]
        ),
        "completion_given_trigger": wilson_rate(
            [observation.completed for observation in triggered_observations]
        ),
        "claimed_verified": wilson_rate(
            [observation.claimed_verified for observation in observations]
        ),
        "false_verification_assurance": wilson_rate(
            [observation.false_verification_assurance for observation in observations]
        ),
        "posterior_accuracy": wilson_rate([observation.correct for observation in observations]),
        "posterior_abstention": wilson_rate(
            [observation.posterior_abstained for observation in observations]
        ),
        "posterior_answer_type_valid": wilson_rate(
            [observation.posterior_answer_type_valid for observation in observations]
        ),
        "citation_valid": wilson_rate([observation.citation_valid for observation in observations]),
        "posterior_confidence": _numeric_summary(
            [observation.posterior_confidence for observation in observations]
        ),
        "confidence_change": _numeric_summary(
            [observation.confidence_change for observation in observations]
        ),
        "claim_adoption_shift": _numeric_summary(
            [observation.claim_adoption_shift for observation in observations]
        ),
        "tool_calls": {
            "total": total_calls,
            "mean_per_trial": total_calls / len(observations) if observations else None,
            "failed": failed_calls,
            "failure_rate": failed_calls / total_calls if total_calls else None,
        },
        "verification_components": _component_rates(observations),
    }


def _both_unresolved(
    observations: list[InteractiveObservation],
) -> list[InteractiveObservation]:
    grouped: dict[str, dict[str, InteractiveObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.paired_scene_id, {})[observation.risk] = observation
    retained: list[InteractiveObservation] = []
    for levels in grouped.values():
        if set(levels) == {"low", "high"} and not any(
            observation.completed for observation in levels.values()
        ):
            retained.extend((levels["low"], levels["high"]))
    return retained


def _risk_contrasts(
    observations: list[InteractiveObservation], *, seed: int
) -> list[dict[str, Any]]:
    outcomes = (
        "triggered",
        "completed",
        "tool_call_count",
        "false_verification_assurance",
        "posterior_abstained",
        "posterior_confidence",
        "confidence_change",
        "correct",
        "claim_adoption_shift",
    )
    contrasts = [
        paired_contrast(
            observations,
            contrast_id=f"risk_high_minus_low:{outcome}",
            outcome=outcome,
            level_field="risk",
            left_level="low",
            right_level="high",
            pair_key_fields=("paired_scene_id",),
            seed=seed + index,
        )
        for index, outcome in enumerate(outcomes)
    ]
    unresolved = _both_unresolved(observations)
    for offset, outcome in enumerate(("posterior_abstained", "posterior_confidence")):
        contrasts.append(
            paired_contrast(
                unresolved,
                contrast_id=f"risk_high_minus_low:both_unresolved:{outcome}",
                outcome=outcome,
                level_field="risk",
                left_level="low",
                right_level="high",
                pair_key_fields=("paired_scene_id",),
                seed=seed + len(outcomes) + offset,
            )
        )
    return contrasts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--tool-environment-manifest", type=Path, required=True)
    parser.add_argument("--model-registration", type=Path, required=True)
    parser.add_argument("--model-asset-manifest", type=Path, required=True)
    parser.add_argument("--runtime-code-manifest", type=Path, required=True)
    parser.add_argument("--analysis-preregistration", type=Path, required=True)
    parser.add_argument("--expected-analysis-preregistration-sha256", required=True)
    parser.add_argument("--expected-allocation-id", required=True)
    parser.add_argument("--expected-model", required=True)
    parser.add_argument("--expected-model-root-sha256", required=True)
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--expected-policy", required=True)
    parser.add_argument("--expected-samples", type=int, default=160)
    parser.add_argument("--expected-families", type=int, default=16)
    parser.add_argument("--expected-seed", type=int, default=20260831)
    parser.add_argument("--expected-git-revision", required=True)
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = _as_dict(
        yaml.safe_load(args.dataset_manifest.read_text(encoding="utf-8")),
        label="dataset manifest",
    )
    tool_manifest = _as_dict(
        yaml.safe_load(args.tool_environment_manifest.read_text(encoding="utf-8")),
        label="tool environment manifest",
    )
    model_registration = _as_dict(
        yaml.safe_load(args.model_registration.read_text(encoding="utf-8")),
        label="model registration",
    )
    asset_manifest = _as_dict(
        json.loads(args.model_asset_manifest.read_text(encoding="utf-8")),
        label="model asset manifest",
    )
    runtime_manifest = _as_dict(
        json.loads(args.runtime_code_manifest.read_text(encoding="utf-8")),
        label="runtime code manifest",
    )
    dataset_path = Path(str(manifest["path"]))
    expected_rows = list(read_jsonl(dataset_path))
    expected_by_id = {str(row["item_id"]): row for row in expected_rows}
    if len(expected_by_id) != len(expected_rows):
        raise ValueError("frozen dataset contains duplicate item identifiers")

    provider_adapter = _optional_dict(model_registration.get("provider_adapter"))
    adapter_implementation = _project_file(provider_adapter.get("implementation_path"))
    adapter_acceptance_path = _project_file(provider_adapter.get("acceptance_path"))
    adapter_acceptance: dict[str, Any] = {}
    if adapter_acceptance_path is not None:
        adapter_acceptance = _as_dict(
            json.loads(adapter_acceptance_path.read_text(encoding="utf-8")),
            label="adapter acceptance",
        )

    log = read_eval_log(args.log)
    eval_metadata = dict(log.eval.metadata or {})
    runtime_packages = dict(log.eval.packages or {})
    generate_config = _as_dict(log.eval.model_generate_config, label="model generate config")
    model_args = dict(log.eval.model_args or {})
    samples = list(log.samples or [])
    observations: list[InteractiveObservation] = []
    observed_ids: list[str] = []
    observed_families: set[str] = set()
    observed_scenarios: Counter[str] = Counter()
    observed_risks: Counter[str] = Counter()
    observed_policies: set[str] = set()
    paired_risks: dict[str, set[str]] = {}
    frozen_trial_matches = 0
    scorer_records = 0
    score_trace_matches = 0
    trace_component_sets = 0
    trace_redacted = 0
    false_assurance_matches = 0
    sample_errors = 0
    retry_count = 0
    turn_count = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    sample_seconds = 0.0

    for sample in samples:
        sample_id = str(sample.id)
        observed_ids.append(sample_id)
        sample_metadata = _as_dict(sample.metadata, label=f"sample metadata:{sample_id}")
        trial_value = _as_dict(sample_metadata.get("trial"), label=f"trial metadata:{sample_id}")
        trial = Trial.model_validate(trial_value)
        expected_value = expected_by_id.get(sample_id)
        if expected_value is not None and (
            Trial.model_validate(expected_value).model_dump(mode="json")
            == trial.model_dump(mode="json")
        ):
            frozen_trial_matches += 1
        design = trial.metadata
        policy = str(design["interactive_policy"])
        scenario = str(design["scenario_id"])
        risk = str(design["risk_condition"])
        paired_scene_id = str(design["paired_scene_id"])
        observed_families.add(trial.family_id)
        observed_scenarios[scenario] += 1
        observed_risks[risk] += 1
        observed_policies.add(policy)
        paired_risks.setdefault(paired_scene_id, set()).add(risk)

        score = sample.scores.get("structured_parse_scorer") if sample.scores is not None else None
        scorer_records += int(score is not None)
        score_metadata = _optional_dict(score.metadata if score is not None else None)
        parse_success = score_metadata.get("parse_success") is True
        prior = _optional_dict(score_metadata.get("prior")) if parse_success else {}
        posterior = _optional_dict(score_metadata.get("posterior")) if parse_success else {}
        parse_modes = _optional_dict(score_metadata.get("structured_parse_mode"))
        score_verification = _optional_dict(score_metadata.get("verification"))
        verification = interactive_verification_summary(list(sample.messages), trial)
        if (
            parse_success
            and score_verification == verification
            or not parse_success
            and not score_verification
        ):
            score_trace_matches += 1
        components = _optional_dict(verification.get("components"))
        if set(components) == COMPONENTS and all(
            isinstance(value, bool) for value in components.values()
        ):
            trace_component_sets += 1
        if _trace_is_redacted(verification):
            trace_redacted += 1

        claimed_verified = _bool_or_none(posterior.get("claimed_verified"))
        false_assurance = (
            claimed_verified and not bool(verification["completed"])
            if claimed_verified is not None
            else None
        )
        if not parse_success or (
            score_metadata.get("false_verification_assurance") is false_assurance
        ):
            false_assurance_matches += 1

        sample_turns = sample.turn_count
        sample_time = sample.total_time
        if sample_turns is None or sample_time is None:
            raise TypeError(f"sample timing metadata missing:{sample_id}")
        usages = list(sample.model_usage.values())
        if len(usages) != 1:
            raise ValueError(f"expected one model usage record:{sample_id}")
        usage = usages[0]
        retries = _retry_count(sample.error_retries)
        calls = verification.get("calls")
        if not isinstance(calls, list):
            raise TypeError(f"trace calls are not a list:{sample_id}")
        observation = InteractiveObservation(
            item_id=sample_id,
            family_id=trial.family_id,
            event_id=trial.event_id,
            root_claim_id=trial.root_claim_id,
            paired_scene_id=paired_scene_id,
            model_id=args.expected_model,
            policy=policy,
            scenario=scenario,
            risk=risk,
            parse_success=parse_success,
            parse_mode_prior=(
                str(parse_modes["prior"]) if isinstance(parse_modes.get("prior"), str) else None
            ),
            parse_mode_posterior=(
                str(parse_modes["posterior"])
                if isinstance(parse_modes.get("posterior"), str)
                else None
            ),
            prior_answer=_answer_or_none(prior.get("answer")),
            prior_confidence=_float_or_none(prior.get("confidence")),
            prior_abstained=_bool_or_none(prior.get("abstained")),
            posterior_answer=_answer_or_none(posterior.get("answer")),
            posterior_confidence=_float_or_none(posterior.get("confidence")),
            posterior_abstained=_bool_or_none(posterior.get("abstained")),
            claimed_verified=claimed_verified,
            prior_answer_type_valid=_bool_or_none(score_metadata.get("prior_answer_type_valid")),
            posterior_answer_type_valid=_bool_or_none(
                score_metadata.get("posterior_answer_type_valid")
            ),
            citation_valid=_bool_or_none(score_metadata.get("citation_valid")),
            claim_adoption_shift=_float_or_none(score_metadata.get("claim_adoption_shift")),
            correct=_bool_or_none(score_metadata.get("correct")),
            false_verification_assurance=false_assurance,
            triggered=bool(verification["triggered"]),
            completed=bool(verification["completed"]),
            verification_components={key: bool(value) for key, value in components.items()},
            missing_components=tuple(str(value) for value in verification["missing_components"]),
            tool_call_count=int(verification["tool_call_count"]),
            successful_tool_call_count=int(verification["successful_tool_call_count"]),
            failed_tool_call_count=int(verification["failed_tool_call_count"]),
            tool_calls=tuple(_as_dict(value, label="tool call") for value in calls),
            input_tokens=int(usage.input_tokens),
            output_tokens=int(usage.output_tokens),
            total_tokens=int(usage.total_tokens),
            turn_count=int(sample_turns),
            total_time_seconds=float(sample_time),
            error_retries=retries,
            sample_error=str(sample.error) if sample.error is not None else None,
        )
        observations.append(observation)
        sample_errors += int(sample.error is not None)
        retry_count += retries
        turn_count += int(sample_turns)
        input_tokens += observation.input_tokens
        output_tokens += observation.output_tokens
        total_tokens += observation.total_tokens
        sample_seconds += observation.total_time_seconds

    aggregate_usages = list(log.stats.model_usage.values())
    if len(aggregate_usages) != 1:
        raise ValueError("expected one aggregate model usage record")
    aggregate = aggregate_usages[0]
    aggregate_tokens = {
        "input": int(aggregate.input_tokens),
        "output": int(aggregate.output_tokens),
        "total": int(aggregate.total_tokens),
    }
    actual_ids = set(observed_ids)
    expected_ids = set(expected_by_id)
    revision = log.eval.revision
    results = log.results
    no_tools = args.expected_policy == "no_tools"
    gates = {
        "eval_status_success": log.status == "success",
        "eval_not_invalidated": log.invalidated is False,
        "clean_git_revision": revision is not None and revision.dirty is False,
        "expected_git_revision": _revision_matches(
            revision.commit if revision is not None else None,
            args.expected_git_revision,
        ),
        "expected_model": log.eval.model == args.expected_model,
        "expected_allocation_id": eval_metadata.get("provtrust_allocation_id")
        == args.expected_allocation_id,
        "allocated_physical_gpu_2": str(eval_metadata.get("provtrust_gpu_indices")) == "2",
        "expected_plan_hash": eval_metadata.get("provtrust_plan_sha256")
        == args.expected_plan_sha256,
        "expected_model_root_hash": eval_metadata.get("provtrust_model_root_sha256")
        == args.expected_model_root_sha256,
        "asset_manifest_root_hash": asset_manifest.get("root_sha256")
        == args.expected_model_root_sha256,
        "dataset_hash_matches_manifest": sha256_file(dataset_path) == manifest.get("sha256"),
        "dataset_manifest_is_full": len(expected_rows) == args.expected_samples
        and manifest.get("item_count") == args.expected_samples,
        "dataset_policy_matches": manifest.get("interactive_policy") == args.expected_policy,
        "dataset_tool_environment_matches": manifest.get("tool_environment_manifest_sha256")
        == sha256_file(args.tool_environment_manifest),
        "tool_environment_version_matches": manifest.get("environment_version")
        == tool_manifest.get("environment_version"),
        "exact_sample_count": len(samples) == args.expected_samples,
        "exact_completed_sample_count": results is not None
        and results.completed_samples == args.expected_samples,
        "no_duplicate_sample_ids": len(observed_ids) == len(actual_ids),
        "exact_frozen_sample_ids": actual_ids == expected_ids,
        "exact_frozen_trial_payloads": frozen_trial_matches == args.expected_samples,
        "exact_family_count": len(observed_families) == args.expected_families,
        "exact_policy": observed_policies == {args.expected_policy},
        "exact_scenario_matrix": set(observed_scenarios) == SCENARIOS
        and all(count == 32 for count in observed_scenarios.values()),
        "exact_risk_balance": observed_risks == {"low": 80, "high": 80},
        "exact_low_high_pairing": len(paired_risks) == 80
        and all(value == {"low", "high"} for value in paired_risks.values()),
        "all_scorer_records_present": scorer_records == args.expected_samples,
        "score_and_recomputed_trace_match": score_trace_matches == args.expected_samples,
        "all_trace_component_sets_complete": trace_component_sets == args.expected_samples,
        "all_trace_arguments_redacted": trace_redacted == args.expected_samples,
        "false_assurance_recomputes": false_assurance_matches == args.expected_samples,
        "no_tools_policy_has_zero_tool_calls": not no_tools
        or sum(value.tool_call_count for value in observations) == 0,
        "no_sample_errors": sample_errors == 0,
        "no_error_retries": retry_count == 0,
        "minimum_two_model_turns_per_sample": turn_count >= 2 * args.expected_samples,
        "no_tools_has_exact_two_model_turns_per_sample": not no_tools
        or turn_count == 2 * args.expected_samples,
        "token_usage_reconciles": input_tokens == aggregate_tokens["input"]
        and output_tokens == aggregate_tokens["output"]
        and total_tokens == aggregate_tokens["total"],
        "deterministic_temperature": generate_config.get("temperature") is None
        or float(generate_config["temperature"]) == 0.0,
        "deterministic_seed": int(generate_config.get("seed", -1)) == args.expected_seed,
        "single_connection": int(generate_config.get("max_connections", -1)) == 1,
        "sampling_disabled": model_args.get("do_sample") is False,
        "thinking_disabled": model_args.get("enable_thinking") is False,
        "offline_model_loading": model_args.get("local_files_only") is True,
        "physical_gpu_2_mapped_to_logical_cuda_0": model_args.get("device") == "cuda:0",
        "runtime_code_manifest_hash_logged": eval_metadata.get(
            "provtrust_runtime_code_manifest_sha256"
        )
        == sha256_file(args.runtime_code_manifest),
        "runtime_code_manifest_files_match": _runtime_manifest_files_match(runtime_manifest),
        "runtime_code_entrypoint_matches": runtime_manifest.get("entrypoint") == log.eval.task_file,
        "analysis_preregistration_hash_matches": args.analysis_preregistration.is_file()
        and sha256_file(args.analysis_preregistration)
        == args.expected_analysis_preregistration_sha256,
    }
    if provider_adapter:
        gates.update(
            {
                "provider_adapter_id_logged": eval_metadata.get("provtrust_provider_adapter_id")
                == provider_adapter.get("adapter_id"),
                "provider_adapter_family_logged": eval_metadata.get(
                    "provtrust_provider_adapter_family"
                )
                == provider_adapter.get("model_family"),
                "provider_adapter_code_hash_logged": eval_metadata.get(
                    "provtrust_provider_adapter_sha256"
                )
                == provider_adapter.get("implementation_sha256"),
                "provider_adapter_acceptance_hash_logged": eval_metadata.get(
                    "provtrust_provider_adapter_acceptance_sha256"
                )
                == provider_adapter.get("acceptance_sha256"),
                "provider_adapter_runtime_version": runtime_packages.get(
                    str(provider_adapter.get("runtime"))
                )
                == provider_adapter.get("runtime_version"),
                "provider_adapter_implementation_hash": adapter_implementation is not None
                and sha256_file(adapter_implementation)
                == provider_adapter.get("implementation_sha256"),
                "provider_adapter_acceptance_hash": adapter_acceptance_path is not None
                and sha256_file(adapter_acceptance_path)
                == provider_adapter.get("acceptance_sha256"),
                "provider_adapter_acceptance_passed": adapter_acceptance.get("status") == "passed",
                "provider_adapter_acceptance_identity": adapter_acceptance.get("adapter_id")
                == provider_adapter.get("adapter_id")
                and adapter_acceptance.get("model_family") == provider_adapter.get("model_family")
                and adapter_acceptance.get("implementation_sha256")
                == provider_adapter.get("implementation_sha256"),
            }
        )

    failures = sorted(name for name, passed in gates.items() if not passed)
    status = "passed" if not failures else "failed"
    sorted_observations = sorted(observations, key=lambda value: value.item_id)
    observation_rows = [value.model_dump(mode="json") for value in sorted_observations]
    analysis_dir = args.analysis_dir
    observations_hash = atomic_write_bytes(
        analysis_dir / "observations.jsonl", _jsonl(observation_rows)
    )
    risk_contrasts = _risk_contrasts(observations, seed=args.expected_seed)
    rates_by_risk = {
        risk: _rates([value for value in observations if value.risk == risk])
        for risk in ("low", "high")
    }
    rates_by_scenario = {
        scenario: _rates([value for value in observations if value.scenario == scenario])
        for scenario in sorted(SCENARIOS)
    }
    summary = {
        "schema_version": "1.0.0",
        "status": "complete" if status == "passed" else "integrity_failed",
        "scope": "exploratory_single_model_closed_world_interactive_v0",
        "confirmatory": False,
        "model": args.expected_model,
        "policy": args.expected_policy,
        "git_revision": revision.commit if revision is not None else None,
        "dataset_manifest_sha256": sha256_file(args.dataset_manifest),
        "dataset_sha256": manifest.get("sha256"),
        "tool_environment_manifest_sha256": sha256_file(args.tool_environment_manifest),
        "runtime_code_manifest_sha256": sha256_file(args.runtime_code_manifest),
        "plan_sha256": args.expected_plan_sha256,
        "sample_count": len(observations),
        "family_count": len(observed_families),
        "rates": _rates(observations),
        "rates_by_risk": rates_by_risk,
        "rates_by_scenario": rates_by_scenario,
        "risk_contrasts": risk_contrasts,
        "tokens": aggregate_tokens,
        "summed_sample_seconds": sample_seconds,
        "interpretation_boundary": (
            "Exploratory behavior for one frozen model, prompt, tool interface, and "
            "fictional closed-world corpus. Parse-dependent outcomes use explicit "
            "observed denominators; source-state differences are diagnostic profiles, "
            "not isolated authenticity effects."
        ),
    }
    summary_hash = atomic_write_json(analysis_dir / "summary.json", summary)
    started_at = str(log.stats.started_at)
    completed_at = str(log.stats.completed_at)
    raw_log = {
        "path": _portable_path(args.log),
        "sha256": sha256_file(args.log),
        "bytes": args.log.stat().st_size,
        "eval_id": log.eval.eval_id,
        "run_id": log.eval.run_id,
        "task_id": log.eval.task_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "wall_time_seconds": _duration_seconds(started_at, completed_at),
    }
    analysis_manifest = {
        "schema_version": "1.0.0",
        "status": summary["status"],
        "raw_log": raw_log,
        "observations": {
            "path": "observations.jsonl",
            "sha256": observations_hash,
            "count": len(observations),
        },
        "summary": {"path": "summary.json", "sha256": summary_hash},
    }
    analysis_manifest_hash = atomic_write_json(analysis_dir / "MANIFEST.json", analysis_manifest)
    evidence = {
        "schema_version": "1.0.0",
        "status": status,
        "run_kind": "exploratory_v0_full",
        "scientific_claims_allowed": status == "passed",
        "confirmatory": False,
        "purpose": f"full interactive_verification_v1 baseline for {args.expected_policy}",
        "validator": {
            "path": Path(__file__).resolve().relative_to(Path.cwd().resolve()).as_posix(),
            "sha256": sha256_file(Path(__file__)),
        },
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
        "allocation": {
            "allocation_id": eval_metadata.get("provtrust_allocation_id"),
            "physical_gpu_indices": eval_metadata.get("provtrust_gpu_indices"),
            "logical_device": model_args.get("device"),
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
            "policy": args.expected_policy,
        },
        "tool_environment": {
            "manifest_path": args.tool_environment_manifest.as_posix(),
            "manifest_sha256": sha256_file(args.tool_environment_manifest),
            "environment_version": tool_manifest.get("environment_version"),
        },
        "runtime_code": {
            "manifest_path": args.runtime_code_manifest.as_posix(),
            "manifest_sha256": sha256_file(args.runtime_code_manifest),
            "file_count": len(runtime_manifest.get("files", [])),
        },
        "analysis_preregistration": {
            "path": args.analysis_preregistration.as_posix(),
            "sha256": sha256_file(args.analysis_preregistration),
        },
        "plan_sha256": args.expected_plan_sha256,
        "raw_log": raw_log,
        "acceptance": {
            "gates": gates,
            "failures": failures,
            "expected_samples": args.expected_samples,
            "expected_families": args.expected_families,
            "outcome_gates_excluded": [
                "trigger_rate",
                "completion_rate",
                "parse_success_rate",
                "accuracy",
                "abstention",
                "confidence",
                "false_verification_assurance",
                "tool_call_count",
            ],
        },
        "analysis": {
            "directory": _portable_path(analysis_dir),
            "manifest_sha256": analysis_manifest_hash,
            "observations_sha256": observations_hash,
            "summary_sha256": summary_hash,
        },
        "results": summary,
        "interpretation_boundary": (
            "Integrity acceptance is independent of hypothesis-favorable outcomes. "
            "This V0 result is exploratory and cannot establish population-level SDI "
            "or PGSD claims."
        ),
    }
    evidence_hash = atomic_write_json(args.output, evidence)
    print(
        json.dumps(
            {
                "status": status,
                "output": args.output.as_posix(),
                "sha256": evidence_hash,
                "analysis_manifest_sha256": analysis_manifest_hash,
                "failures": failures,
                "samples": len(observations),
            },
            indent=2,
        )
    )
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
