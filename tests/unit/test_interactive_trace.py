from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from inspect_ai.model import ChatMessageAssistant, ChatMessageTool
from inspect_ai.tool import ToolCall

from provtrust.datasets.interactive_v0 import InteractivePolicy, build_interactive_assets
from provtrust.datasets.v0_corpus import V0CorpusSpec
from provtrust.scorers.interactive_trace import interactive_verification_summary


def _assets() -> Any:
    value = yaml.safe_load(
        Path("configs/datasets/v0_paired_v1.yaml").read_text(encoding="utf-8")
    )
    return build_interactive_assets(
        V0CorpusSpec.model_validate(value), InteractivePolicy.TOOLS_PROMPTED
    )


def _tool_messages(
    function: str, arguments: dict[str, Any], output: Any, sequence: int
) -> list[object]:
    call_id = f"call-{sequence}"
    return [
        ChatMessageAssistant(
            content="",
            tool_calls=[
                ToolCall(id=call_id, function=function, arguments=arguments)
            ],
        ),
        ChatMessageTool(
            content=json.dumps(output),
            tool_call_id=call_id,
            function=function,
        ),
    ]


def test_trial_specific_trace_requires_every_semantic_component() -> None:
    assets = _assets()
    trial = next(
        trial
        for trial in assets.trials
        if trial.metadata["scenario_id"] == "c3_false_attribution"
        and trial.metadata["risk_condition"] == "high"
    )
    metadata = trial.metadata
    canonical_id = str(metadata["expected_canonical_document_id"])
    presented_id = str(metadata["presented_document_id"])
    canonical_document = next(
        document for document in assets.documents if document["document_id"] == canonical_id
    )
    presented_document = next(
        document for document in assets.documents if document["document_id"] == presented_id
    )
    canonical_text = str(canonical_document["text"])
    evidence_text = str(metadata["expected_evidence_text"])
    start = canonical_text.index(evidence_text)
    messages: list[object] = []
    messages += _tool_messages(
        "canonical_lookup",
        {"source_name_or_id": "Aster Canonical Registry"},
        [{"source_id": metadata["expected_canonical_source_id"]}],
        1,
    )
    messages += _tool_messages(
        "controlled_search",
        {"query": trial.question, "limit": 10},
        [canonical_document, presented_document],
        2,
    )
    messages += _tool_messages(
        "open_snapshot",
        {
            "document_id": canonical_id,
            "expected_sha256": metadata["expected_canonical_snapshot_sha256"],
        },
        {
            "document_id": canonical_id,
            "sha256": metadata["expected_canonical_snapshot_sha256"],
            "text": canonical_text,
        },
        3,
    )
    messages += _tool_messages(
        "verify_identifier",
        {
            "identifier": metadata["presented_identifier"],
            "kind": "announcement",
        },
        {
            "identifier": metadata["presented_identifier"],
            "registry_match": False,
        },
        4,
    )
    messages += _tool_messages(
        "find_evidence",
        {"document": canonical_text, "needle": evidence_text, "ignore_case": True},
        [{"start": start, "end": start + len(evidence_text), "text": evidence_text}],
        5,
    )
    messages += _tool_messages(
        "provenance_trace",
        {"document_id": presented_id},
        {
            "status": "found",
            "record": {
                "published_at": presented_document["published_at"],
                "edges": [{"verified": False}],
            },
        },
        6,
    )

    summary = interactive_verification_summary(messages, trial)  # type: ignore[arg-type]
    assert summary["triggered"] is True
    assert summary["completed"] is True
    assert summary["missing_components"] == []

    incomplete = interactive_verification_summary(messages[:-2], trial)  # type: ignore[arg-type]
    assert incomplete["completed"] is False
    assert "conflict_temporality_checked" in incomplete["missing_components"]
