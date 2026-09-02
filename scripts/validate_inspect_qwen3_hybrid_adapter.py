"""Model-free acceptance for the frozen hybrid Inspect/Qwen3 tool parser."""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

from inspect_ai.model._providers.util import hf_handler

from provtrust.execution.atomic_io import atomic_write_json, sha256_file
from provtrust.execution.inspect_qwen3_hybrid import (
    QWEN3_14B_HYBRID_ADAPTER_ID,
    QWEN3_14B_HYBRID_MODEL_NAME,
    QWEN3_14B_HYBRID_TOOL_FAMILY,
    parse_qwen3_hybrid_tool_response,
    register_qwen3_14b_hybrid_tool_adapter,
)


def _case(name: str, passed: bool, observed: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "observed": observed}


def _evaluate(
    name: str,
    response: str,
    expected_content: str,
    expected_calls: list[str],
) -> dict[str, Any]:
    content, calls = parse_qwen3_hybrid_tool_response(response)
    return _case(
        name,
        content == expected_content and calls == expected_calls,
        {
            "content_preserved": content == expected_content,
            "tool_calls_match": calls == expected_calls,
            "tool_call_count": len(calls),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    final_json = (
        '{"answer":null,"confidence":0,"abstained":true,'
        '"claimed_verified":false,"cited_evidence_ids":[],"declared_factors":{}}'
    )
    fenced_final = f"```json\n{final_json}\n```"
    tool_json = (
        '{"name":"find_evidence","arguments":'
        '{"document":"Aster record","needle":"amber seal"}}'
    )
    tagged_tool = f"<tool_call>{tool_json}</tool_call>"
    fenced_tool = f"```json\n{tool_json}\n```"

    generic_content, generic_calls = hf_handler.model_specific_tool_parse(
        fenced_final, QWEN3_14B_HYBRID_MODEL_NAME
    )
    cases = [
        _case(
            "generic_route_reproduces_original_final_json_failure",
            generic_content == "" and generic_calls == [final_json],
            {
                "remaining_content": generic_content,
                "tool_call_count": len(generic_calls),
            },
        ),
        _evaluate("raw_final_json_is_content", final_json, final_json, []),
        _evaluate("fenced_final_json_is_content", fenced_final, fenced_final, []),
        _evaluate("tagged_tool_call_is_extracted", tagged_tool, "", [tool_json]),
        _evaluate("fenced_tool_call_is_extracted", fenced_tool, "", [tool_json]),
        _evaluate("raw_tool_call_is_extracted", tool_json, "", [tool_json]),
        _evaluate(
            "mixed_content_and_tagged_call_are_separated",
            f"Checking the registry.\n{tagged_tool}",
            "Checking the registry.",
            [tool_json],
        ),
        _evaluate(
            "non_tool_json_with_name_text_is_preserved",
            '{"answer":"the words name and arguments are mentioned"}',
            '{"answer":"the words name and arguments are mentioned"}',
            [],
        ),
    ]

    info = register_qwen3_14b_hybrid_tool_adapter()
    installed_content, installed_calls = hf_handler.model_specific_tool_parse(
        fenced_tool, QWEN3_14B_HYBRID_TOOL_FAMILY
    )
    cases.append(
        _case(
            "installed_dispatch_uses_hybrid_route",
            installed_content == "" and installed_calls == [tool_json],
            {
                "remaining_content": installed_content,
                "tool_call_count": len(installed_calls),
            },
        )
    )

    implementation = Path("src/provtrust/execution/inspect_qwen3_hybrid.py")
    validator = Path("scripts/validate_inspect_qwen3_hybrid_adapter.py")
    upstream_parser = Path(hf_handler.__file__)
    runtime_version = version("inspect_ai")
    passed = (
        info.family == QWEN3_14B_HYBRID_TOOL_FAMILY
        and runtime_version == "0.3.261"
        and all(case["passed"] for case in cases)
    )
    report = {
        "schema_version": "1.0.0",
        "status": "passed" if passed else "failed",
        "purpose": "model-free acceptance of the hybrid Inspect/Qwen3 tool parser",
        "adapter_id": QWEN3_14B_HYBRID_ADAPTER_ID,
        "registration_model_name": QWEN3_14B_HYBRID_MODEL_NAME,
        "model_family": QWEN3_14B_HYBRID_TOOL_FAMILY,
        "runtime": "inspect_ai",
        "runtime_version": runtime_version,
        "implementation_path": implementation.as_posix(),
        "implementation_sha256": sha256_file(implementation),
        "validator_path": validator.as_posix(),
        "validator_sha256": sha256_file(validator),
        "upstream_parser_path": "inspect_ai/model/_providers/util/hf_handler.py",
        "upstream_parser_sha256": sha256_file(upstream_parser),
        "cases": cases,
        "scientific_claims_allowed": False,
        "interpretation_boundary": (
            "This artifact validates representation normalization only; it does not "
            "validate model decisions, verification completeness, or answer quality."
        ),
    }
    artifact_hash = atomic_write_json(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": args.output.as_posix(),
                "sha256": artifact_hash,
            },
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
