"""Versioned Inspect compatibility registrations for frozen local models."""

from __future__ import annotations

from inspect_ai.model import ModelInfo, get_model_info, set_model_info

QWEN3_14B_INSPECT_MODEL_NAME = "Qwen/Qwen3-14B"
QWEN3_14B_INSPECT_TOOL_FAMILY = "Qwen3-Instruct"
QWEN3_14B_INSPECT_ADAPTER_ID = "inspect-hf-qwen3-instruct-tool-parser-v1"


def register_qwen3_14b_hf_tool_adapter() -> ModelInfo:
    """Route Qwen3-14B through Inspect's Qwen-Instruct tool parser.

    Inspect 0.3.261 selects its Hugging Face tool parser from model-family
    metadata. The upstream Qwen3 repository name contains neither ``instruct``
    nor ``coder``, so the generic fallback mistakes fenced final-answer JSON for
    a tool call. This registration changes parser routing only: the provider and
    model identifier sent to Hugging Face remain unchanged.
    """

    info = ModelInfo(
        organization="Qwen",
        model="Qwen3-14B",
        context_length=32768,
        output_tokens=32768,
        family=QWEN3_14B_INSPECT_TOOL_FAMILY,
    )
    set_model_info(QWEN3_14B_INSPECT_MODEL_NAME, info)
    observed = get_model_info(QWEN3_14B_INSPECT_MODEL_NAME)
    if observed is None or observed.family != QWEN3_14B_INSPECT_TOOL_FAMILY:
        raise RuntimeError("Qwen3 Hugging Face tool-parser registration did not take effect")
    return observed
