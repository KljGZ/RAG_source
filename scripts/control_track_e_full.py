"""Allowlisted one-shot controller for the frozen Track E V0 full-run queue."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import control_track_e as controller
import yaml

from provtrust.execution.atomic_io import sha256_file

controller.CONTROLLER_ID = "track-e-v4-full-run-queue"
controller.CONTROLLER_CONFIG = "configs/controller/track_e_v4_full.local.yaml"
controller.CONTROLLER_SCRIPT = "scripts/control_track_e_full.py"
controller.STATE_DIRECTORY_NAME = "track-e-v4-full"
controller.ALLOWED_PLAN_QUEUE = (
    (
        "interactive-v3-no-tools-full",
        "configs/experiments/v0_qwen3_14b_interactive_v3_no_tools.yaml",
        "d577a34b63c62a8a63a90cc31d875af50d82e14e138a59b3c7ae27e9949ade91",
    ),
    (
        "interactive-v3-tools-unprompted-full",
        "configs/experiments/v0_qwen3_14b_interactive_v3_tools_unprompted.yaml",
        "94267a7e83ca351d8c5629e8f85348d8deee9af319f033f4400b2d743dd44878",
    ),
    (
        "interactive-v3-tools-prompted-full",
        "configs/experiments/v0_qwen3_14b_interactive_v3_tools_prompted.yaml",
        "91f24c14e67f6f0810b5d5b9b76fc6507a77e28ebbf7b7833217cd820aeef312",
    ),
)

_EXPECTED_POLICIES = {
    "interactive-v3-no-tools-full": "no_tools",
    "interactive-v3-tools-unprompted-full": "tools_unprompted",
    "interactive-v3-tools-prompted-full": "tools_prompted",
}
_ANALYSIS_PLAN = "analysis/preregistration/V0_INTERACTIVE_VERIFICATION_ANALYSIS_PLAN.md"
_BASE_PLAN_ENTRIES = controller._plan_entries


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object:{path}")
    return value


def _validate_full_plan(root: Path, entry: dict[str, Any]) -> None:
    plan_path = Path(entry["resolved_path"])
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        raise TypeError(f"full plan is not an object:{entry['name']}")
    name = str(entry["name"])
    expected_policy = _EXPECTED_POLICIES[name]
    expected_scalars = {
        "input_contract_version": 7,
        "stage": "v0",
        "execution_status": "ready",
        "exploratory": True,
        "scientific_claims_allowed": True,
        "confirmatory": False,
        "track": "interactive_verification",
        "interactive_policy": expected_policy,
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

    evidence_path = controller._project_file(
        root, plan.get("activation_evidence"), f"activation_evidence:{name}"
    )
    if sha256_file(evidence_path) != plan.get("activation_evidence_sha256"):
        raise ValueError(f"full plan activation evidence hash mismatch:{name}")
    evidence = _load_json(evidence_path)
    identity = plan.get("activation_identity")
    if not isinstance(identity, dict):
        raise TypeError(f"full plan activation identity missing:{name}")
    raw_log = evidence.get("raw_log")
    evidence_model = evidence.get("model")
    evidence_dataset = evidence.get("dataset")
    evidence_acceptance = evidence.get("acceptance")
    if not isinstance(raw_log, dict):
        raise TypeError(f"full plan activation raw log missing:{name}")
    if not isinstance(evidence_model, dict) or not isinstance(evidence_dataset, dict):
        raise TypeError(f"full plan activation metadata missing:{name}")
    if not isinstance(evidence_acceptance, dict):
        raise TypeError(f"full plan activation gates missing:{name}")
    preflight_revision = identity.get("preflight_git_revision")
    observed_revision = evidence_model.get("revision")
    if not (
        evidence.get("status") == "passed"
        and evidence.get("run_kind") == "preflight"
        and evidence.get("scientific_claims_allowed") is False
        and evidence.get("plan_sha256") == identity.get("preflight_plan_sha256")
        and raw_log.get("sha256") == identity.get("preflight_raw_log_sha256")
        and isinstance(preflight_revision, str)
        and isinstance(observed_revision, str)
        and preflight_revision.startswith(observed_revision)
        and evidence_dataset.get("policy") == expected_policy
        and evidence_acceptance.get("failures") == []
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
