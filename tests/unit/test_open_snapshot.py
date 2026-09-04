from __future__ import annotations

import asyncio
import json
from pathlib import Path

from inspect_ai.model import ChatMessageAssistant, ChatMessageTool, execute_tools
from inspect_ai.tool import ToolCall

from provtrust.datasets.io import read_jsonl
from provtrust.tools.open_snapshot import open_snapshot

INDEX_PATH = Path("web_env/search_index/documents.jsonl")
SNAPSHOT_ROOT = Path("web_env/source_snapshots")
MISSING_DOCUMENT_ID = "v0-family-002:c5_missing_reference:presented"


def _known_document_id() -> str:
    first = next(iter(read_jsonl(INDEX_PATH)))
    return str(first["document_id"])


def test_unknown_document_is_a_nonfatal_structured_tool_error() -> None:
    snapshot_tool = open_snapshot(INDEX_PATH.as_posix(), SNAPSHOT_ROOT.as_posix())
    messages = [
        ChatMessageAssistant(
            content="",
            tool_calls=[
                ToolCall(
                    id="missing",
                    function="open_snapshot",
                    arguments={"document_id": MISSING_DOCUMENT_ID},
                )
            ],
        )
    ]

    result = asyncio.run(execute_tools(messages, [snapshot_tool]))

    assert len(result.messages) == 1
    message = result.messages[0]
    assert isinstance(message, ChatMessageTool)
    assert message.error is not None
    assert message.error.type == "unknown"
    assert json.loads(message.error.message) == {
        "status": "not_found",
        "error_code": "unknown_controlled_document",
        "document_id": MISSING_DOCUMENT_ID,
    }


def test_unknown_document_does_not_cancel_parallel_valid_open() -> None:
    known_document_id = _known_document_id()
    snapshot_tool = open_snapshot(INDEX_PATH.as_posix(), SNAPSHOT_ROOT.as_posix())
    messages = [
        ChatMessageAssistant(
            content="",
            tool_calls=[
                ToolCall(
                    id="missing",
                    function="open_snapshot",
                    arguments={"document_id": MISSING_DOCUMENT_ID},
                ),
                ToolCall(
                    id="known",
                    function="open_snapshot",
                    arguments={"document_id": known_document_id},
                ),
            ],
        )
    ]

    result = asyncio.run(execute_tools(messages, [snapshot_tool]))
    by_call_id = {
        message.tool_call_id: message
        for message in result.messages
        if isinstance(message, ChatMessageTool)
    }

    assert set(by_call_id) == {"missing", "known"}
    assert by_call_id["missing"].error is not None
    assert by_call_id["known"].error is None
    assert json.loads(by_call_id["known"].text)["document_id"] == known_document_id
