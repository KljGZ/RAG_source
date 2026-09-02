from __future__ import annotations

from inspect_ai.model import get_model_info
from inspect_ai.model._providers.util.hf_handler import model_specific_tool_parse

from provtrust.execution.inspect_compat import (
    QWEN3_14B_INSPECT_MODEL_NAME,
    QWEN3_14B_INSPECT_TOOL_FAMILY,
    register_qwen3_14b_hf_tool_adapter,
)


def test_qwen3_registration_selects_instruct_family_without_renaming_model() -> None:
    registered = register_qwen3_14b_hf_tool_adapter()
    observed = get_model_info(QWEN3_14B_INSPECT_MODEL_NAME)

    assert observed is not None
    assert registered.family == QWEN3_14B_INSPECT_TOOL_FAMILY
    assert observed.family == QWEN3_14B_INSPECT_TOOL_FAMILY
    assert QWEN3_14B_INSPECT_MODEL_NAME == "Qwen/Qwen3-14B"


def test_qwen_instruct_parser_distinguishes_answer_json_from_tool_calls() -> None:
    answer = '```json\n{"answer":null,"confidence":0,"abstained":true}\n```'
    content, calls = model_specific_tool_parse(answer, QWEN3_14B_INSPECT_TOOL_FAMILY)
    assert content == answer
    assert calls == []

    tool_call = (
        '<tool_call>{"name":"controlled_search",'
        '"arguments":{"query":"ASTER-A01"}}</tool_call>'
    )
    content, calls = model_specific_tool_parse(
        tool_call, QWEN3_14B_INSPECT_TOOL_FAMILY
    )
    assert content == ""
    assert calls == [
        '{"name":"controlled_search","arguments":{"query":"ASTER-A01"}}'
    ]
