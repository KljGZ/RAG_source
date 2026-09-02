"""Project-scoped hybrid tool parser for Qwen3 on Inspect's HF provider."""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from inspect_ai.model import ModelInfo, get_model_info, set_model_info
from inspect_ai.model._providers.util import hf_handler

QWEN3_14B_HYBRID_MODEL_NAME = "Qwen/Qwen3-14B"
QWEN3_14B_HYBRID_TOOL_FAMILY = "Qwen3-ProvTrust-Hybrid-v2"
QWEN3_14B_HYBRID_ADAPTER_ID = "inspect-hf-qwen3-hybrid-tool-parser-v2"

_ToolParser = Callable[[str, str], tuple[str, list[str]]]
_UPSTREAM_TOOL_PARSE: _ToolParser = hf_handler.model_specific_tool_parse
_TOOL_TAG = re.compile(r"<tool_call>((?:.|\n)*?)</tool_call>", re.DOTALL)
_JSON_FENCE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def _is_tool_envelope(value: str) -> bool:
    try:
        payload = json.loads(value.strip())
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("name"), str)
        and bool(payload["name"])
        and "arguments" in payload
    )


def parse_qwen3_hybrid_tool_response(response: str) -> tuple[str, list[str]]:
    """Separate Qwen3 tool envelopes while preserving final-answer JSON.

    The frozen Qwen3 snapshot emits official ``<tool_call>`` envelopes on some
    turns and fenced JSON envelopes on others. Classification is structural:
    fenced or raw JSON is treated as a tool call only when its top-level object
    contains a non-empty ``name`` and an ``arguments`` field. The study's final
    answer schema has neither field and is therefore returned byte-for-byte as
    ordinary assistant content.
    """

    tagged_calls = [match.strip() for match in _TOOL_TAG.findall(response)]
    if tagged_calls:
        content = _TOOL_TAG.sub("", response).strip()
        return content, tagged_calls

    fenced_calls = [match.strip() for match in _JSON_FENCE.findall(response)]
    if fenced_calls and all(_is_tool_envelope(call) for call in fenced_calls):
        content = _JSON_FENCE.sub("", response).strip()
        return content, fenced_calls

    stripped = response.strip()
    if _is_tool_envelope(stripped):
        return "", [stripped]
    return response, []


def _dispatch_qwen3_hybrid_tool_parse(
    response: str, model_name: str
) -> tuple[str, list[str]]:
    if model_name.casefold() == QWEN3_14B_HYBRID_TOOL_FAMILY.casefold():
        return parse_qwen3_hybrid_tool_response(response)
    return _UPSTREAM_TOOL_PARSE(response, model_name)


def register_qwen3_14b_hybrid_tool_adapter() -> ModelInfo:
    """Install and verify the frozen, model-scoped Qwen3 parser route."""

    current = hf_handler.model_specific_tool_parse
    if current is not _dispatch_qwen3_hybrid_tool_parse:
        if current is not _UPSTREAM_TOOL_PARSE:
            raise RuntimeError("Inspect HF tool parser was modified by an unknown component")
        hf_handler.model_specific_tool_parse = _dispatch_qwen3_hybrid_tool_parse

    info = ModelInfo(
        organization="Qwen",
        model="Qwen3-14B",
        context_length=32768,
        output_tokens=32768,
        family=QWEN3_14B_HYBRID_TOOL_FAMILY,
    )
    set_model_info(QWEN3_14B_HYBRID_MODEL_NAME, info)
    observed = get_model_info(QWEN3_14B_HYBRID_MODEL_NAME)
    if observed is None or observed.family != QWEN3_14B_HYBRID_TOOL_FAMILY:
        raise RuntimeError("Qwen3 hybrid parser-family registration did not take effect")
    if hf_handler.model_specific_tool_parse is not _dispatch_qwen3_hybrid_tool_parse:
        raise RuntimeError("Qwen3 hybrid parser dispatch did not take effect")
    return observed
