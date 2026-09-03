"""Trial-specific verification predicates over Inspect tool-call transcripts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from inspect_ai.model import ChatMessage, ChatMessageAssistant, ChatMessageTool

from provtrust.schemas.trial import Trial

VERIFICATION_TOOLS = frozenset(
    {
        "canonical_lookup",
        "controlled_search",
        "open_snapshot",
        "verify_identifier",
        "find_evidence",
        "provenance_trace",
    }
)


@dataclass(frozen=True)
class _CallRecord:
    call_id: str
    function: str
    arguments: dict[str, Any]
    succeeded: bool
    output_text: str
    decoded: Any
    error: str | None


def _decode_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None


def _records(messages: list[ChatMessage]) -> tuple[_CallRecord, ...]:
    requested: dict[str, tuple[str, dict[str, Any]]] = {}
    ordered_ids: list[str] = []
    for message in messages:
        if not isinstance(message, ChatMessageAssistant):
            continue
        for call in message.tool_calls or []:
            requested[call.id] = (call.function, dict(call.arguments))
            ordered_ids.append(call.id)

    completed: dict[str, _CallRecord] = {}
    for message in messages:
        if not isinstance(message, ChatMessageTool):
            continue
        call_id = message.tool_call_id or message.id or "unmatched"
        function, arguments = requested.get(call_id, (message.function or "unknown", {}))
        output_text = message.text
        completed[call_id] = _CallRecord(
            call_id=call_id,
            function=message.function or function,
            arguments=arguments,
            succeeded=message.error is None,
            output_text=output_text,
            decoded=_decode_json(output_text),
            error=str(message.error) if message.error is not None else None,
        )

    records: list[_CallRecord] = []
    for call_id in ordered_ids:
        if call_id in completed:
            records.append(completed[call_id])
            continue
        function, arguments = requested[call_id]
        records.append(
            _CallRecord(
                call_id=call_id,
                function=function,
                arguments=arguments,
                succeeded=False,
                output_text="",
                decoded=None,
                error="missing_tool_result",
            )
        )
    for call_id, record in completed.items():
        if call_id not in requested:
            records.append(record)
    return tuple(records)


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _safe_arguments(record: _CallRecord) -> dict[str, Any]:
    arguments = dict(record.arguments)
    document = arguments.get("document")
    if isinstance(document, str):
        arguments["document"] = {
            "sha256": hashlib.sha256(document.encode("utf-8")).hexdigest(),
            "characters": len(document),
        }
    return arguments


def _canonical_resolved(records: tuple[_CallRecord, ...], source_id: str) -> bool:
    return any(
        record.succeeded
        and record.function == "canonical_lookup"
        and any(str(row.get("source_id")) == source_id for row in _rows(record.decoded))
        for record in records
    )


def _search_components(
    records: tuple[_CallRecord, ...],
    canonical_document_id: str,
    presented_document_id: str,
    *,
    page_exists: bool,
) -> tuple[bool, bool]:
    searches = tuple(
        record
        for record in records
        if record.succeeded
        and record.function == "controlled_search"
        and isinstance(record.decoded, list)
    )
    hits = [row for record in searches for row in _rows(record.decoded)]
    identifiers = {str(hit.get("document_id")) for hit in hits}
    canonical_found = canonical_document_id in identifiers
    if page_exists:
        presented_checked = presented_document_id in identifiers
    else:
        target = presented_document_id.casefold()
        targeted_searches = tuple(
            record
            for record in searches
            if isinstance(record.arguments.get("query"), str)
            and target in str(record.arguments["query"]).casefold()
        )
        presented_checked = bool(targeted_searches) and all(
            presented_document_id
            not in {str(row.get("document_id")) for row in _rows(record.decoded)}
            for record in targeted_searches
        )
    return canonical_found, presented_checked


def _canonical_opened(
    records: tuple[_CallRecord, ...], document_id: str, expected_sha256: str
) -> bool:
    return any(
        record.succeeded
        and record.function == "open_snapshot"
        and isinstance(record.decoded, dict)
        and record.decoded.get("document_id") == document_id
        and record.decoded.get("sha256") == expected_sha256
        for record in records
    )


def _identifier_checked(
    records: tuple[_CallRecord, ...], identifier: str, should_match: bool
) -> bool:
    return any(
        record.succeeded
        and record.function == "verify_identifier"
        and record.arguments.get("identifier") == identifier
        and isinstance(record.decoded, dict)
        and record.decoded.get("identifier") == identifier
        and record.decoded.get("registry_match") is should_match
        for record in records
    )


def _evidence_span_recorded(
    records: tuple[_CallRecord, ...], expected_document_sha256: str, expected_text: str
) -> bool:
    expected_folded = expected_text.casefold()
    for record in records:
        if not record.succeeded or record.function != "find_evidence":
            continue
        document = record.arguments.get("document")
        needle = record.arguments.get("needle")
        if not isinstance(document, str) or not isinstance(needle, str):
            continue
        if hashlib.sha256(document.encode("utf-8")).hexdigest() != expected_document_sha256:
            continue
        normalized = needle.strip().casefold()
        if len(normalized) < 8 or normalized not in expected_folded:
            continue
        matches = _rows(record.decoded)
        if any(
            isinstance(row.get("start"), int)
            and isinstance(row.get("end"), int)
            and int(row["start"]) < int(row["end"])
            and str(row.get("text", "")).casefold() == normalized
            for row in matches
        ):
            return True
    return False


def _temporal_trace_checked(
    records: tuple[_CallRecord, ...], presented_document_id: str, page_exists: bool
) -> bool:
    for record in records:
        if (
            not record.succeeded
            or record.function != "provenance_trace"
            or record.arguments.get("document_id") != presented_document_id
            or not isinstance(record.decoded, dict)
        ):
            continue
        status = record.decoded.get("status")
        if not page_exists:
            return status == "not_found"
        provenance = record.decoded.get("record")
        if status != "found" or not isinstance(provenance, dict):
            continue
        if isinstance(provenance.get("published_at"), str) and isinstance(
            provenance.get("edges"), list
        ):
            return True
    return False


def interactive_verification_summary(messages: list[ChatMessage], trial: Trial) -> dict[str, Any]:
    """Evaluate completed verification against this trial's frozen gold trace."""

    metadata = trial.metadata
    if metadata.get("stimulus_protocol") != "interactive_verification_v1":
        raise ValueError("interactive trace scorer requires interactive_verification_v1")
    source_id = str(metadata["expected_canonical_source_id"])
    canonical_document_id = str(metadata["expected_canonical_document_id"])
    presented_document_id = str(metadata["presented_document_id"])
    expected_sha256 = str(metadata["expected_canonical_snapshot_sha256"])
    expected_text_sha256 = str(metadata["expected_canonical_text_sha256"])
    expected_evidence = str(metadata["expected_evidence_text"])
    identifier = str(metadata["presented_identifier"])
    identifier_should_match = bool(metadata["presented_identifier_should_match"])
    page_exists = bool(metadata["page_exists"])
    temporal_required = bool(metadata["requires_temporal_check"])

    records = _records(messages)
    canonical_search, presented_existence_checked = _search_components(
        records,
        canonical_document_id,
        presented_document_id,
        page_exists=page_exists,
    )
    components = {
        "canonical_source_resolved": _canonical_resolved(records, source_id),
        "canonical_record_found": canonical_search,
        "presented_record_existence_checked": presented_existence_checked,
        "canonical_snapshot_opened": _canonical_opened(
            records, canonical_document_id, expected_sha256
        ),
        "claimed_identifier_checked": _identifier_checked(
            records, identifier, identifier_should_match
        ),
        "canonical_evidence_span_recorded": _evidence_span_recorded(
            records, expected_text_sha256, expected_evidence
        ),
        "conflict_temporality_checked": (
            True
            if not temporal_required
            else _temporal_trace_checked(records, presented_document_id, page_exists)
        ),
    }
    completed = all(components.values())
    attempted = [record for record in records if record.function in VERIFICATION_TOOLS]
    successful = [record for record in attempted if record.succeeded]
    call_rows = [
        {
            "call_id": record.call_id,
            "tool_name": record.function,
            "arguments": _safe_arguments(record),
            "succeeded": record.succeeded,
            "output_sha256": hashlib.sha256(record.output_text.encode("utf-8")).hexdigest(),
            "error": record.error,
        }
        for record in records
    ]
    return {
        "definition": "trial_specific_interactive_v2",
        "triggered": bool(attempted),
        "completed": completed,
        "components": components,
        "missing_components": sorted(name for name, value in components.items() if not value),
        "tool_call_count": len(attempted),
        "successful_tool_call_count": len(successful),
        "failed_tool_call_count": len(attempted) - len(successful),
        "tool_failure_rate": (
            (len(attempted) - len(successful)) / len(attempted) if attempted else None
        ),
        "calls": call_rows,
    }
