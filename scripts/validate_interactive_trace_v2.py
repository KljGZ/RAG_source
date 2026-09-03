"""Model-free acceptance for the version-2 interactive trace definition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from inspect_ai.model import ChatMessageAssistant, ChatMessageTool
from inspect_ai.tool import ToolCall

from provtrust.datasets.interactive_v0 import InteractivePolicy, build_interactive_assets
from provtrust.datasets.v0_corpus import V0CorpusSpec
from provtrust.execution.atomic_io import atomic_write_json, sha256_file
from provtrust.scorers.interactive_trace import interactive_verification_summary


def _tool_messages(
    function: str, arguments: dict[str, Any], output: Any, sequence: int
) -> list[Any]:
    call_id = f"acceptance-{sequence}"
    return [
        ChatMessageAssistant(
            content="",
            tool_calls=[ToolCall(id=call_id, function=function, arguments=arguments)],
        ),
        ChatMessageTool(
            content=json.dumps(output),
            tool_call_id=call_id,
            function=function,
        ),
    ]


def _component(messages: list[Any], trial: Any) -> bool:
    summary = interactive_verification_summary(messages, trial)
    return bool(summary["components"]["presented_record_existence_checked"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-config", type=Path, default=Path("configs/datasets/v0_paired_v1.yaml")
    )
    parser.add_argument(
        "--amendment",
        type=Path,
        default=Path(
            "analysis/preregistration/" "V0_INTERACTIVE_VERIFICATION_ENGINEERING_AMENDMENT_003.md"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    spec_value = yaml.safe_load(args.dataset_config.read_text(encoding="utf-8"))
    assets = build_interactive_assets(
        V0CorpusSpec.model_validate(spec_value), InteractivePolicy.TOOLS_PROMPTED
    )
    missing = next(
        trial
        for trial in assets.trials
        if trial.metadata["scenario_id"] == "c5_missing_reference"
        and trial.metadata["risk_condition"] == "high"
    )
    existing = next(
        trial
        for trial in assets.trials
        if trial.metadata["page_exists"] is True and trial.metadata["risk_condition"] == "high"
    )
    missing_id = str(missing.metadata["presented_document_id"])
    existing_id = str(existing.metadata["presented_document_id"])
    existing_document = next(row for row in assets.documents if row["document_id"] == existing_id)

    unrelated = _tool_messages("controlled_search", {"query": missing.question, "limit": 10}, [], 1)
    targeted = _tool_messages(
        "controlled_search", {"query": missing_id.upper(), "limit": 10}, [], 2
    )
    invalid = _tool_messages("controlled_search", {"query": missing_id, "limit": 10}, {}, 3)
    contradictory = _tool_messages(
        "controlled_search",
        {"query": missing_id, "limit": 10},
        [{"document_id": missing_id}],
        4,
    )
    missing_call_id = "acceptance-missing-result"
    missing_result = [
        ChatMessageAssistant(
            content="",
            tool_calls=[
                ToolCall(
                    id=missing_call_id,
                    function="controlled_search",
                    arguments={"query": missing_id, "limit": 10},
                )
            ],
        )
    ]
    positive = _tool_messages(
        "controlled_search",
        {"query": existing.question, "limit": 10},
        [existing_document],
        5,
    )

    targeted_summary = interactive_verification_summary(targeted, missing)
    gates = {
        "definition_is_v2": targeted_summary.get("definition") == "trial_specific_interactive_v2",
        "no_call_does_not_establish_absence": not _component([], missing),
        "unrelated_empty_search_does_not_establish_absence": not _component(unrelated, missing),
        "target_bound_empty_search_establishes_absence": _component(targeted, missing),
        "missing_tool_result_does_not_establish_absence": not _component(missing_result, missing),
        "invalid_result_type_does_not_establish_absence": not _component(invalid, missing),
        "contradictory_hit_does_not_establish_absence": not _component(contradictory, missing),
        "returned_existing_record_establishes_existence": _component(positive, existing),
        "single_component_never_implies_strict_completion": targeted_summary.get("completed")
        is False,
    }
    failures = sorted(name for name, passed in gates.items() if not passed)
    scorer_path = Path("src/provtrust/scorers/interactive_trace.py")
    validator_path = Path(__file__).resolve()
    root = Path.cwd().resolve()
    report = {
        "schema_version": "1.0.0",
        "status": "passed" if not failures else "failed",
        "run_kind": "model_free_trace_semantics_acceptance",
        "scientific_claims_allowed": False,
        "definition": "trial_specific_interactive_v2",
        "acceptance": {"gates": gates, "failures": failures},
        "scorer": {
            "path": scorer_path.as_posix(),
            "sha256": sha256_file(scorer_path),
        },
        "amendment": {
            "path": args.amendment.as_posix(),
            "sha256": sha256_file(args.amendment),
        },
        "dataset_config": {
            "path": args.dataset_config.as_posix(),
            "sha256": sha256_file(args.dataset_config),
        },
        "validator": {
            "path": validator_path.relative_to(root).as_posix(),
            "sha256": sha256_file(validator_path),
        },
        "interpretation_boundary": (
            "This model-free artifact validates trace semantics only; it contains no model "
            "behavior and supports no behavioral claim."
        ),
    }
    artifact_hash = atomic_write_json(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": args.output.as_posix(),
                "sha256": artifact_hash,
                "failures": failures,
            },
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
