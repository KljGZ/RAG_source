"""Model-free acceptance for nonfatal unknown-document tool behavior."""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any

from inspect_ai.model import ChatMessageAssistant, ChatMessageTool, execute_tools
from inspect_ai.tool import ToolCall

from provtrust.datasets.io import read_jsonl
from provtrust.execution.atomic_io import atomic_write_json, sha256_file
from provtrust.schemas.trial import Trial
from provtrust.scorers.interactive_trace import interactive_verification_summary
from provtrust.tools.open_snapshot import open_snapshot

DATASET = Path("benchmark/synthetic/v0-interactive-v1-tools_prompted.jsonl")
SEARCH_INDEX = Path("web_env/search_index/documents.jsonl")
SNAPSHOT_ROOT = Path("web_env/source_snapshots")
SNAPSHOT_MANIFEST = Path("web_env/source_snapshots/MANIFEST.json")
TOOL_SOURCE = Path("src/provtrust/tools/open_snapshot.py")
SCORER_SOURCE = Path("src/provtrust/scorers/interactive_trace.py")


def _missing_trial() -> Trial:
    trials = (Trial.model_validate(row) for row in read_jsonl(DATASET))
    return next(
        trial
        for trial in trials
        if trial.metadata["scenario_id"] == "c5_missing_reference"
        and trial.metadata["risk_condition"] == "low"
    )


def _tool_messages_by_id(messages: list[Any]) -> dict[str, ChatMessageTool]:
    return {
        str(message.tool_call_id): message
        for message in messages
        if isinstance(message, ChatMessageTool)
    }


async def _exercise(trial: Trial) -> tuple[list[Any], dict[str, Any]]:
    presented_id = str(trial.metadata["presented_document_id"])
    canonical_id = str(trial.metadata["expected_canonical_document_id"])
    expected_sha256 = str(trial.metadata["expected_canonical_snapshot_sha256"])
    assistant = ChatMessageAssistant(
        content="",
        tool_calls=[
            ToolCall(
                id="missing-presented",
                function="open_snapshot",
                arguments={"document_id": presented_id},
            ),
            ToolCall(
                id="valid-canonical",
                function="open_snapshot",
                arguments={
                    "document_id": canonical_id,
                    "expected_sha256": expected_sha256,
                },
            ),
        ],
    )
    result = await execute_tools(
        [assistant],
        [open_snapshot(SEARCH_INDEX.as_posix(), SNAPSHOT_ROOT.as_posix())],
    )
    messages = [assistant, *result.messages]
    by_id = _tool_messages_by_id(result.messages)
    missing = by_id.get("missing-presented")
    known = by_id.get("valid-canonical")
    missing_payload: Any = None
    if missing is not None and missing.error is not None:
        try:
            missing_payload = json.loads(missing.error.message)
        except json.JSONDecodeError:
            missing_payload = None
    known_payload: Any = None
    if known is not None and known.error is None:
        try:
            known_payload = json.loads(known.text)
        except json.JSONDecodeError:
            known_payload = None
    return messages, {
        "message_count": len(result.messages),
        "missing_error_type": missing.error.type
        if missing is not None and missing.error is not None
        else None,
        "missing_error_payload": missing_payload,
        "known_payload": known_payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trial = _missing_trial()
    messages, observed = asyncio.run(_exercise(trial))
    summary = interactive_verification_summary(messages, trial)
    presented_id = str(trial.metadata["presented_document_id"])
    canonical_id = str(trial.metadata["expected_canonical_document_id"])
    expected_sha256 = str(trial.metadata["expected_canonical_snapshot_sha256"])
    expected_error = {
        "status": "not_found",
        "error_code": "unknown_controlled_document",
        "document_id": presented_id,
    }
    known_payload = observed["known_payload"]
    gates = {
        "two_parallel_results_retained": observed["message_count"] == 2,
        "unknown_document_is_tool_error": observed["missing_error_type"] == "unknown",
        "unknown_document_error_is_structured": observed["missing_error_payload"]
        == expected_error,
        "parallel_valid_open_completed": isinstance(known_payload, dict)
        and known_payload.get("document_id") == canonical_id,
        "parallel_valid_open_hash_matches": isinstance(known_payload, dict)
        and known_payload.get("sha256") == expected_sha256,
        "trace_records_both_calls": summary["tool_call_count"] == 2,
        "trace_records_one_failed_call": summary["failed_tool_call_count"] == 1,
        "trace_records_one_successful_call": summary["successful_tool_call_count"] == 1,
        "failed_open_does_not_establish_absence": summary["components"][
            "presented_record_existence_checked"
        ]
        is False,
        "valid_canonical_open_is_retained": summary["components"][
            "canonical_snapshot_opened"
        ]
        is True,
        "partial_trace_is_not_completion": summary["completed"] is False,
    }
    failures = sorted(name for name, passed in gates.items() if not passed)
    validator = Path(__file__).resolve()
    root = Path.cwd().resolve()
    report = {
        "schema_version": "1.0.0",
        "status": "passed" if not failures else "failed",
        "acceptance_id": "open_snapshot_fault_containment_v1",
        "purpose": (
            "prove that an unknown controlled document remains a failed model-selected "
            "tool call without terminating the sample or cancelling a parallel valid call"
        ),
        "model_calls": 0,
        "torch_imported": "torch" in sys.modules,
        "inspect_ai_version": importlib.metadata.version("inspect-ai"),
        "validator": {
            "path": validator.relative_to(root).as_posix(),
            "sha256": sha256_file(validator),
        },
        "inputs": {
            path.as_posix(): sha256_file(path)
            for path in (
                DATASET,
                SEARCH_INDEX,
                SNAPSHOT_MANIFEST,
                TOOL_SOURCE,
                SCORER_SOURCE,
            )
        },
        "trial": {
            "item_id": trial.item_id,
            "scenario": trial.metadata["scenario_id"],
            "risk": trial.metadata["risk_condition"],
            "presented_document_id": presented_id,
            "canonical_document_id": canonical_id,
        },
        "observed": observed,
        "trace": {
            "definition": summary["definition"],
            "triggered": summary["triggered"],
            "completed": summary["completed"],
            "tool_call_count": summary["tool_call_count"],
            "successful_tool_call_count": summary["successful_tool_call_count"],
            "failed_tool_call_count": summary["failed_tool_call_count"],
            "components": summary["components"],
        },
        "acceptance": {"gates": gates, "failures": failures},
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
