"""Allowlisted one-shot controller for corrected Track E V0 full-run plans."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import control_track_e as controller
import yaml

from provtrust.execution.atomic_io import sha256_file

controller.CONTROLLER_ID = "track-e-v5-corrected-full-run-queue"
controller.CONTROLLER_CONFIG = "configs/controller/track_e_v5_full.local.yaml"
controller.CONTROLLER_SCRIPT = "scripts/control_track_e_v5_full.py"
controller.STATE_DIRECTORY_NAME = "track-e-v5-full"
controller.ALLOWED_PLAN_QUEUE = (
    (
        "interactive-v4-no-tools-full",
        "configs/experiments/v0_qwen3_14b_interactive_v4_no_tools.yaml",
        "8c0c533adaf354e282a27c5abba591908a1f1a297ac14239243304c5af30bdf9",
    ),
    (
        "interactive-v4-tools-unprompted-full",
        "configs/experiments/v0_qwen3_14b_interactive_v4_tools_unprompted.yaml",
        "e2375120c5662ce14a769875b5b0937b483d4815739d444ed73d0399a1673d83",
    ),
    (
        "interactive-v4-tools-prompted-full",
        "configs/experiments/v0_qwen3_14b_interactive_v4_tools_prompted.yaml",
        "48078d10cc338df88c194baab34757184e0ce098741ca16ecf41e9f8615b7d67",
    ),
)

_EXPECTED_POLICIES = {
    "interactive-v4-no-tools-full": "no_tools",
    "interactive-v4-tools-unprompted-full": "tools_unprompted",
    "interactive-v4-tools-prompted-full": "tools_prompted",
}
_ANALYSIS_PLAN = "analysis/preregistration/V0_INTERACTIVE_VERIFICATION_ANALYSIS_PLAN.md"
_AMENDMENT = "analysis/preregistration/V0_INTERACTIVE_VERIFICATION_ENGINEERING_AMENDMENT_003.md"
_RUNTIME_MANIFEST = "configs/runtime/interactive-v2-qwen3-full-v2.manifest.json"
_TRACE_ACCEPTANCE = "artifacts/system/INTERACTIVE_TRACE_V2_ACCEPTANCE.json"
_SCORER_DEFINITION = "trial_specific_interactive_v2"
_BASE_PLAN_ENTRIES = controller._plan_entries


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object:{path}")
    return value


def _all_gates_passed(value: Any) -> bool:
    if not isinstance(value, dict) or value.get("failures") != []:
        return False
    gates = value.get("gates")
    return (
        isinstance(gates, dict) and bool(gates) and all(passed is True for passed in gates.values())
    )


def _frozen_json(
    root: Path, plan: dict[str, Any], field: str, expected_path: str | None = None
) -> dict[str, Any]:
    path = controller._project_file(root, plan.get(field), field)
    if expected_path is not None and plan.get(field) != expected_path:
        raise ValueError(f"full plan {field} path mismatch")
    if sha256_file(path) != plan.get(f"{field}_sha256"):
        raise ValueError(f"full plan {field} hash mismatch")
    return _load_json(path)


def _validate_full_plan(root: Path, entry: dict[str, Any]) -> None:
    plan_path = Path(entry["resolved_path"])
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        raise TypeError(f"full plan is not an object:{entry['name']}")
    name = str(entry["name"])
    expected_policy = _EXPECTED_POLICIES[name]
    expected_scalars = {
        "input_contract_version": 8,
        "stage": "v0",
        "execution_status": "ready",
        "exploratory": True,
        "scientific_claims_allowed": True,
        "confirmatory": False,
        "track": "interactive_verification",
        "interactive_policy": expected_policy,
        "scorer_definition": _SCORER_DEFINITION,
        "run_kind": "exploratory_v0_full",
        "sample_count": 160,
        "family_count": 16,
        "scenario_count": 5,
        "seed": 20260831,
        "epochs": 1,
        "retry_on_error": 0,
    }
    mismatched = [key for key, expected in expected_scalars.items() if plan.get(key) != expected]
    if mismatched:
        raise ValueError(f"full plan contract mismatch:{name}:{','.join(mismatched)}")

    analysis_path = controller._project_file(
        root, plan.get("analysis_preregistration"), f"analysis_preregistration:{name}"
    )
    if plan.get("analysis_preregistration") != _ANALYSIS_PLAN:
        raise ValueError(f"full plan analysis path mismatch:{name}")
    if sha256_file(analysis_path) != plan.get("analysis_preregistration_sha256"):
        raise ValueError(f"full plan analysis hash mismatch:{name}")

    amendment_path = controller._project_file(
        root, plan.get("engineering_amendment"), f"engineering_amendment:{name}"
    )
    if plan.get("engineering_amendment") != _AMENDMENT:
        raise ValueError(f"full plan amendment path mismatch:{name}")
    if sha256_file(amendment_path) != plan.get("engineering_amendment_sha256"):
        raise ValueError(f"full plan amendment hash mismatch:{name}")

    runtime = _frozen_json(root, plan, "runtime_code_manifest", _RUNTIME_MANIFEST)
    if runtime.get("manifest_id") != "interactive-v2-qwen3-full-v2":
        raise ValueError(f"full plan runtime identity mismatch:{name}")
    trace_acceptance = _frozen_json(root, plan, "trace_scorer_acceptance", _TRACE_ACCEPTANCE)
    if not (
        trace_acceptance.get("status") == "passed"
        and trace_acceptance.get("definition") == _SCORER_DEFINITION
        and _all_gates_passed(trace_acceptance.get("acceptance"))
    ):
        raise ValueError(f"full plan trace acceptance mismatch:{name}")

    evidence = _frozen_json(root, plan, "activation_evidence")
    identity = plan.get("activation_identity")
    if not isinstance(identity, dict):
        raise TypeError(f"full plan activation identity missing:{name}")
    source = evidence.get("source_preflight")
    raw_log = evidence.get("raw_log")
    rescore = evidence.get("rescore")
    scorer = evidence.get("scorer")
    scorer_acceptance = evidence.get("scorer_acceptance")
    evidence_amendment = evidence.get("amendment")
    if not all(
        isinstance(value, dict)
        for value in (source, raw_log, rescore, scorer, scorer_acceptance, evidence_amendment)
    ):
        raise TypeError(f"full plan rescore evidence is incomplete:{name}")
    assert isinstance(source, dict)
    assert isinstance(raw_log, dict)
    assert isinstance(rescore, dict)
    assert isinstance(scorer, dict)
    assert isinstance(scorer_acceptance, dict)
    assert isinstance(evidence_amendment, dict)
    preflight_revision = identity.get("preflight_git_revision")
    observed_revision = source.get("git_revision")
    if not (
        evidence.get("status") == "passed"
        and evidence.get("run_kind") == "preflight_rescore"
        and evidence.get("scientific_claims_allowed") is False
        and evidence.get("policy") == expected_policy
        and _all_gates_passed(evidence.get("acceptance"))
        and source.get("sha256") == identity.get("source_preflight_sha256")
        and source.get("plan_sha256") == identity.get("preflight_plan_sha256")
        and raw_log.get("sha256") == identity.get("preflight_raw_log_sha256")
        and raw_log.get("immutable") is True
        and isinstance(preflight_revision, str)
        and isinstance(observed_revision, str)
        and preflight_revision.startswith(observed_revision)
        and rescore.get("definition") == identity.get("rescore_definition")
        and rescore.get("definition") == _SCORER_DEFINITION
        and rescore.get("no_new_model_output") is True
        and rescore.get("sample_count") == 10
        and scorer.get("sha256") == identity.get("rescore_scorer_sha256")
        and scorer.get("new_definition") == _SCORER_DEFINITION
        and scorer_acceptance.get("sha256") == identity.get("scorer_acceptance_sha256")
        and scorer_acceptance.get("sha256") == plan.get("trace_scorer_acceptance_sha256")
        and evidence_amendment.get("sha256") == plan.get("engineering_amendment_sha256")
    ):
        raise ValueError(f"full plan activation identity mismatch:{name}")

    inspect_command = plan.get("inspect_command")
    analysis_command = plan.get("analysis_command")
    if not isinstance(inspect_command, list) or not all(
        isinstance(value, str) for value in inspect_command
    ):
        raise TypeError(f"full plan inspect command invalid:{name}")
    if "--limit" in inspect_command:
        raise ValueError(f"full plan may not limit the frozen dataset:{name}")
    if (
        inspect_command.count("--max-connections") != 1
        or inspect_command.count("--max-samples") != 1
    ):
        raise ValueError(f"full plan concurrency is not explicit:{name}")
    if not isinstance(analysis_command, list) or analysis_command[:2] != [
        "python",
        "scripts/analyze_interactive_run.py",
    ]:
        raise ValueError(f"full plan analysis command invalid:{name}")
    if _RUNTIME_MANIFEST not in analysis_command:
        raise ValueError(f"full plan analysis runtime mismatch:{name}")
    if analysis_command.count("PLAN_SHA256") != 1 or analysis_command.count("GIT_REVISION") != 1:
        raise ValueError(f"full plan analysis identity placeholders invalid:{name}")


def _full_plan_entries(config: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    entries = _BASE_PLAN_ENTRIES(config, root)
    for entry in entries:
        _validate_full_plan(root, entry)
    return entries


controller._plan_entries = _full_plan_entries


if __name__ == "__main__":
    raise SystemExit(controller.main())
