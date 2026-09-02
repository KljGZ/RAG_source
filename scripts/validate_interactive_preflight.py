"""Validate and freeze an interactive-verification compatibility preflight."""

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
    if not isinstance(value, str) or not value:
        return None
    relative = Path(value)
    if relative.is_absolute():
        return None
    root = Path.cwd().resolve()
    resolved = (root / relative).resolve()
    if resolved == root or root not in resolved.parents or not resolved.is_file():
        return None
    return resolved


def _revision_matches(observed: str | None, expected: str | None) -> bool:
    """Accept Git's unambiguous short display of the same expected revision."""

    if expected is None:
        return True
    if observed is None or len(observed) < 7 or len(expected) < 7:
        return False
    return observed.startswith(expected) or expected.startswith(observed)


def _expected_rows(
    manifest: dict[str, Any], expected_samples: int
) -> tuple[list[dict[str, Any]], Path]:
    dataset_path = Path(str(manifest["path"]))
    rows = list(read_jsonl(dataset_path))
    if len(rows) < expected_samples:
        raise ValueError("frozen dataset is smaller than the requested preflight")
    return rows[:expected_samples], dataset_path


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--tool-environment-manifest", type=Path, required=True)
    parser.add_argument("--model-registration", type=Path, required=True)
    parser.add_argument("--model-asset-manifest", type=Path, required=True)
    parser.add_argument("--expected-model", required=True)
    parser.add_argument("--expected-model-root-sha256", required=True)
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--expected-policy", required=True)
    parser.add_argument("--expected-samples", type=int, default=10)
    parser.add_argument("--expected-families", type=int, default=1)
    parser.add_argument("--expected-seed", type=int, default=20260831)
    parser.add_argument("--expected-git-revision")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = yaml.safe_load(args.dataset_manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise TypeError("dataset manifest must contain an object")
    tool_manifest = yaml.safe_load(
        args.tool_environment_manifest.read_text(encoding="utf-8")
    )
    if not isinstance(tool_manifest, dict):
        raise TypeError("tool environment manifest must contain an object")
    expected_rows, dataset_path = _expected_rows(manifest, args.expected_samples)
    expected_by_id = {str(row["item_id"]): row for row in expected_rows}
    if len(expected_by_id) != args.expected_samples:
        raise ValueError("preflight reference rows contain duplicate item identifiers")

    asset_manifest = json.loads(args.model_asset_manifest.read_text(encoding="utf-8"))
    if not isinstance(asset_manifest, dict):
        raise TypeError("model asset manifest must contain an object")
    model_registration = yaml.safe_load(
        args.model_registration.read_text(encoding="utf-8")
    )
    if not isinstance(model_registration, dict):
        raise TypeError("model registration must contain an object")
    provider_adapter = _optional_dict(model_registration.get("provider_adapter"))
    adapter_implementation = _project_file(provider_adapter.get("implementation_path"))
    adapter_acceptance_path = _project_file(provider_adapter.get("acceptance_path"))
    adapter_acceptance: dict[str, Any] = {}
    if adapter_acceptance_path is not None:
        try:
            adapter_acceptance = _optional_dict(
                json.loads(adapter_acceptance_path.read_text(encoding="utf-8"))
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            adapter_acceptance = {}

    log = read_eval_log(args.log)
    eval_metadata = dict(log.eval.metadata or {})
    runtime_packages = dict(log.eval.packages or {})
    generate_config = _as_dict(log.eval.model_generate_config, label="model_generate_config")
    model_args = dict(log.eval.model_args or {})
    samples = list(log.samples or [])

    observed_ids: list[str] = []
    observed_families: set[str] = set()
    observed_scenarios: Counter[str] = Counter()
    observed_risks: Counter[str] = Counter()
    observed_policies: set[str] = set()
    sample_rows: list[dict[str, Any]] = []
    parse_success_count = 0
    score_metadata_count = 0
    prior_type_valid_count = 0
    posterior_type_valid_count = 0
    citation_valid_count = 0
    trace_metadata_valid_count = 0
    trace_redacted_count = 0
    triggered_count = 0
    completed_count = 0
    claimed_verified_count = 0
    false_assurance_count = 0
    correct_count = 0
    abstained_count = 0
    tool_call_count = 0
    failed_tool_call_count = 0
    retry_count = 0
    sample_error_count = 0
    turn_count = 0
    sample_input_tokens = 0
    sample_output_tokens = 0
    sample_total_tokens = 0
    sample_seconds = 0.0

    for sample in samples:
        sample_id = str(sample.id)
        observed_ids.append(sample_id)
        metadata = _as_dict(sample.metadata, label=f"sample metadata: {sample_id}")
        trial = _as_dict(metadata.get("trial"), label=f"trial metadata: {sample_id}")
        claim = _as_dict(trial.get("claim"), label=f"claim metadata: {sample_id}")
        design = _as_dict(trial.get("metadata"), label=f"design metadata: {sample_id}")
        family_id = str(claim["family_id"])
        scenario = str(design["scenario_id"])
        risk = str(design["risk_condition"])
        policy = str(design["interactive_policy"])
        observed_families.add(family_id)
        observed_scenarios[scenario] += 1
        observed_risks[risk] += 1
        observed_policies.add(policy)

        score = (
            sample.scores.get("structured_parse_scorer")
            if sample.scores is not None
            else None
        )
        score_metadata = _optional_dict(score.metadata if score is not None else None)
        prior = _optional_dict(score_metadata.get("prior"))
        posterior = _optional_dict(score_metadata.get("posterior"))
        verification = _optional_dict(score_metadata.get("verification"))
        calls = verification.get("calls")
        calls_list = calls if isinstance(calls, list) else []
        trace_valid = (
            verification.get("definition") == "trial_specific_interactive_v1"
            and isinstance(verification.get("triggered"), bool)
            and isinstance(verification.get("completed"), bool)
            and isinstance(verification.get("components"), dict)
            and isinstance(verification.get("missing_components"), list)
            and isinstance(verification.get("tool_call_count"), int)
            and verification.get("tool_call_count") == len(calls_list)
            and isinstance(verification.get("successful_tool_call_count"), int)
            and isinstance(verification.get("failed_tool_call_count"), int)
            and verification.get("successful_tool_call_count")
            + verification.get("failed_tool_call_count")
            == verification.get("tool_call_count")
        )
        trace_redacted = _trace_is_redacted(verification)
        parse_success = score_metadata.get("parse_success") is True
        prior_type_valid = score_metadata.get("prior_answer_type_valid") is True
        posterior_type_valid = score_metadata.get("posterior_answer_type_valid") is True
        citation_valid = score_metadata.get("citation_valid") is True
        triggered = verification.get("triggered") is True
        completed = verification.get("completed") is True
        claimed_verified = posterior.get("claimed_verified") is True
        false_assurance = score_metadata.get("false_verification_assurance") is True
        correct = score_metadata.get("correct") is True
        abstained = posterior.get("abstained") is True
        sample_tool_calls = int(verification.get("tool_call_count", 0) or 0)
        sample_failed_calls = int(verification.get("failed_tool_call_count", 0) or 0)

        score_metadata_count += int(bool(score_metadata))
        parse_success_count += int(parse_success)
        prior_type_valid_count += int(prior_type_valid)
        posterior_type_valid_count += int(posterior_type_valid)
        citation_valid_count += int(citation_valid)
        trace_metadata_valid_count += int(trace_valid)
        trace_redacted_count += int(trace_redacted)
        triggered_count += int(triggered)
        completed_count += int(completed)
        claimed_verified_count += int(claimed_verified)
        false_assurance_count += int(false_assurance)
        correct_count += int(correct)
        abstained_count += int(abstained)
        tool_call_count += sample_tool_calls
        failed_tool_call_count += sample_failed_calls
        retry_count += _retry_count(sample.error_retries)
        sample_error_count += int(sample.error is not None)

        sample_turns = sample.turn_count
        sample_time = sample.total_time
        if sample_turns is None or sample_time is None:
            raise TypeError(f"sample timing metadata missing: {sample_id}")
        turn_count += sample_turns
        sample_seconds += sample_time
        usages = list(sample.model_usage.values())
        if len(usages) != 1:
            raise ValueError(f"expected one model usage record: {sample_id}")
        usage = usages[0]
        sample_input_tokens += int(usage.input_tokens)
        sample_output_tokens += int(usage.output_tokens)
        sample_total_tokens += int(usage.total_tokens)

        expected = expected_by_id.get(sample_id)
        expected_metadata = expected.get("metadata") if expected is not None else None
        expected_policy = (
            str(expected_metadata.get("interactive_policy"))
            if isinstance(expected_metadata, dict)
            else None
        )
        sample_rows.append(
            {
                "item_id": sample_id,
                "family_id": family_id,
                "scenario": scenario,
                "risk": risk,
                "policy": policy,
                "expected_policy": expected_policy,
                "parse_success": parse_success,
                "prior_answer_type_valid": prior_type_valid,
                "posterior_answer_type_valid": posterior_type_valid,
                "citation_valid": citation_valid,
                "trace_metadata_valid": trace_valid,
                "trace_redacted": trace_redacted,
                "triggered": triggered,
                "completed": completed,
                "claimed_verified": claimed_verified,
                "false_verification_assurance": false_assurance,
                "correct": correct,
                "abstained": abstained,
                "prior_confidence": prior.get("confidence"),
                "posterior_confidence": posterior.get("confidence"),
                "claim_adoption_shift": score_metadata.get("claim_adoption_shift"),
                "tool_call_count": sample_tool_calls,
                "failed_tool_call_count": sample_failed_calls,
                "turn_count": sample_turns,
                "total_tokens": int(usage.total_tokens),
                "error_retries": _retry_count(sample.error_retries),
                "sample_error": str(sample.error) if sample.error is not None else None,
                "score_explanation": score.explanation if score is not None else None,
            }
        )

    aggregate_usages = list(log.stats.model_usage.values())
    if len(aggregate_usages) != 1:
        raise ValueError("expected one aggregate model usage record")
    aggregate = aggregate_usages[0]
    aggregate_tokens = {
        "input": int(aggregate.input_tokens),
        "output": int(aggregate.output_tokens),
        "total": int(aggregate.total_tokens),
    }
    expected_ids = set(expected_by_id)
    actual_ids = set(observed_ids)
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
        "expected_plan_hash": eval_metadata.get("provtrust_plan_sha256")
        == args.expected_plan_sha256,
        "expected_model_root_hash": eval_metadata.get("provtrust_model_root_sha256")
        == args.expected_model_root_sha256,
        "asset_manifest_root_hash": asset_manifest.get("root_sha256")
        == args.expected_model_root_sha256,
        "dataset_hash_matches_manifest": sha256_file(dataset_path) == manifest.get("sha256"),
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
        "exact_family_count": len(observed_families) == args.expected_families,
        "exact_policy": observed_policies == {args.expected_policy}
        and all(row["expected_policy"] == args.expected_policy for row in sample_rows),
        "exact_scenario_matrix": len(observed_scenarios) == 5
        and all(count == 2 for count in observed_scenarios.values()),
        "exact_risk_balance": observed_risks == {"low": 5, "high": 5},
        "all_score_metadata_present": score_metadata_count == args.expected_samples,
        "all_structured_outputs_parse": parse_success_count == args.expected_samples,
        "all_prior_answer_types_valid": prior_type_valid_count == args.expected_samples,
        "all_posterior_answer_types_valid": posterior_type_valid_count
        == args.expected_samples,
        "all_citations_reference_supplied_evidence": citation_valid_count
        == args.expected_samples,
        "all_trace_metadata_valid": trace_metadata_valid_count == args.expected_samples,
        "all_trace_arguments_redacted": trace_redacted_count == args.expected_samples,
        "no_tools_policy_has_zero_tool_calls": not no_tools or tool_call_count == 0,
        "no_sample_errors": sample_error_count == 0,
        "no_error_retries": retry_count == 0,
        "minimum_two_model_turns_per_sample": turn_count >= 2 * args.expected_samples,
        "no_tools_has_exact_two_model_turns_per_sample": not no_tools
        or turn_count == 2 * args.expected_samples,
        "token_usage_reconciles": sample_input_tokens == aggregate_tokens["input"]
        and sample_output_tokens == aggregate_tokens["output"]
        and sample_total_tokens == aggregate_tokens["total"],
        "deterministic_temperature": generate_config.get("temperature") is None
        or float(generate_config["temperature"]) == 0.0,
        "deterministic_seed": int(generate_config.get("seed", -1)) == args.expected_seed,
        "single_connection": int(generate_config.get("max_connections", -1)) == 1,
        "sampling_disabled": model_args.get("do_sample") is False,
        "thinking_disabled": model_args.get("enable_thinking") is False,
        "offline_model_loading": model_args.get("local_files_only") is True,
        "physical_gpu_2_mapped_to_logical_cuda_0": model_args.get("device") == "cuda:0",
    }
    if provider_adapter:
        gates.update(
            {
                "provider_adapter_id_logged": eval_metadata.get(
                    "provtrust_provider_adapter_id"
                )
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
                "provider_adapter_implementation_hash": adapter_implementation
                is not None
                and sha256_file(adapter_implementation)
                == provider_adapter.get("implementation_sha256"),
                "provider_adapter_acceptance_hash": adapter_acceptance_path
                is not None
                and sha256_file(adapter_acceptance_path)
                == provider_adapter.get("acceptance_sha256"),
                "provider_adapter_acceptance_passed": adapter_acceptance.get("status")
                == "passed",
                "provider_adapter_acceptance_identity": adapter_acceptance.get(
                    "adapter_id"
                )
                == provider_adapter.get("adapter_id")
                and adapter_acceptance.get("model_family")
                == provider_adapter.get("model_family")
                and adapter_acceptance.get("implementation_sha256")
                == provider_adapter.get("implementation_sha256"),
            }
        )
    failures = sorted(name for name, passed in gates.items() if not passed)
    status = "passed" if not failures else "failed"
    started_at = str(log.stats.started_at)
    completed_at = str(log.stats.completed_at)
    report = {
        "schema_version": "1.0.0",
        "status": status,
        "run_kind": "preflight",
        "scientific_claims_allowed": False,
        "purpose": (
            "execution and observability acceptance for one-family "
            f"interactive_verification_v1 policy {args.expected_policy}"
        ),
        "interpretation_boundary": (
            "Trigger, completion, accuracy, confidence, abstention, tool failures, and "
            "false assurance are descriptive observations and are not activation gates."
        ),
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
        "provider_adapter": {
            "configured": bool(provider_adapter),
            "adapter_id": provider_adapter.get("adapter_id"),
            "runtime": provider_adapter.get("runtime"),
            "runtime_version": provider_adapter.get("runtime_version"),
            "model_family": provider_adapter.get("model_family"),
            "implementation_path": provider_adapter.get("implementation_path"),
            "implementation_sha256": provider_adapter.get("implementation_sha256"),
            "acceptance_path": provider_adapter.get("acceptance_path"),
            "acceptance_sha256": provider_adapter.get("acceptance_sha256"),
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
            "expected_item_ids": sorted(expected_ids),
        },
        "tool_environment": {
            "manifest_path": args.tool_environment_manifest.as_posix(),
            "manifest_sha256": sha256_file(args.tool_environment_manifest),
            "environment_version": tool_manifest.get("environment_version"),
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
        },
        "observations": {
            "sample_count": len(samples),
            "family_count": len(observed_families),
            "scenario_counts": dict(sorted(observed_scenarios.items())),
            "risk_counts": dict(sorted(observed_risks.items())),
            "parse_success_count": parse_success_count,
            "triggered_count": triggered_count,
            "completed_count": completed_count,
            "claimed_verified_count": claimed_verified_count,
            "false_verification_assurance_count": false_assurance_count,
            "correct_count": correct_count,
            "abstained_count": abstained_count,
            "tool_call_count": tool_call_count,
            "failed_tool_call_count": failed_tool_call_count,
            "sample_error_count": sample_error_count,
            "error_retry_count": retry_count,
            "model_turn_count": turn_count,
            "aggregate_tokens": aggregate_tokens,
            "summed_sample_seconds": round(sample_seconds, 6),
        },
        "samples": sorted(sample_rows, key=lambda row: str(row["item_id"])),
        "warnings": [
            "This is an engineering preflight; its behavioral outcomes are not pooled into V1.",
            (
                "A model-requested tool error remains a behavioral/interface observation. "
                "The separate model-free environment acceptance establishes tool semantics."
            ),
        ],
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
