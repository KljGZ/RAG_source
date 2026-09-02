from __future__ import annotations

from inspect_ai.model._providers.util import hf_handler

from provtrust.execution.inspect_qwen3_hybrid import (
    QWEN3_14B_HYBRID_TOOL_FAMILY,
    parse_qwen3_hybrid_tool_response,
    register_qwen3_14b_hybrid_tool_adapter,
)


def test_hybrid_parser_preserves_answers_and_accepts_both_tool_forms() -> None:
    final = '```json\n{"answer":true,"declared_factors":{}}\n```'
    assert parse_qwen3_hybrid_tool_response(final) == (final, [])

    tool_json = '{"name":"controlled_search","arguments":{"query":"Aster"}}'
    assert parse_qwen3_hybrid_tool_response(
        f"<tool_call>{tool_json}</tool_call>"
    ) == ("", [tool_json])
    assert parse_qwen3_hybrid_tool_response(f"```json\n{tool_json}\n```") == (
        "",
        [tool_json],
    )


def test_hybrid_registration_is_model_family_scoped_and_idempotent() -> None:
    first = register_qwen3_14b_hybrid_tool_adapter()
    second = register_qwen3_14b_hybrid_tool_adapter()
    assert first.family == second.family == QWEN3_14B_HYBRID_TOOL_FAMILY

    response = '```json\n{"name":"controlled_search","arguments":{"query":"Aster"}}\n```'
    content, calls = hf_handler.model_specific_tool_parse(
        response, QWEN3_14B_HYBRID_TOOL_FAMILY
    )
    assert content == ""
    assert len(calls) == 1
