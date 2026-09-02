"""Model-free acceptance for the frozen Inspect/Qwen3 HF tool-parser route."""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

from inspect_ai.model._providers.util import hf_handler

from provtrust.execution.atomic_io import atomic_write_json, sha256_file
from provtrust.execution.inspect_compat import (
    QWEN3_14B_INSPECT_ADAPTER_ID,
    QWEN3_14B_INSPECT_MODEL_NAME,
    QWEN3_14B_INSPECT_TOOL_FAMILY,
    register_qwen3_14b_hf_tool_adapter,
)


def _case(name: str, passed: bool, observed: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "observed": observed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    info = register_qwen3_14b_hf_tool_adapter()
    final_json = (
        '{"answer":null,"confidence":0,"abstained":true,'
        '"claimed_verified":false,"cited_evidence_ids":[],"declared_factors":{}}'
    )
    fenced_final = f"```json\n{final_json}\n```"
    tool_payload = (
        '<tool_call>{"name":"controlled_search",'
        '"arguments":{"query":"ASTER-A01"}}</tool_call>'
    )
    mixed_tool_payload = f"Checking the registry.\n{tool_payload}"

    cases: list[dict[str, Any]] = []
    for case_name, response in (
        ("raw_final_json_is_content", final_json),
        ("fenced_final_json_is_content", fenced_final),
    ):
        content, calls = hf_handler.model_specific_tool_parse(
            response, QWEN3_14B_INSPECT_TOOL_FAMILY
        )
        cases.append(
            _case(
                case_name,
                content == response and calls == [],
                {"content_preserved": content == response, "tool_call_count": len(calls)},
            )
        )

    content, calls = hf_handler.model_specific_tool_parse(
        tool_payload, QWEN3_14B_INSPECT_TOOL_FAMILY
    )
    cases.append(
        _case(
            "tagged_tool_call_is_extracted",
            content == ""
            and calls
            == ['{"name":"controlled_search","arguments":{"query":"ASTER-A01"}}'],
            {"remaining_content": content, "tool_call_count": len(calls)},
        )
    )

    content, calls = hf_handler.model_specific_tool_parse(
        mixed_tool_payload, QWEN3_14B_INSPECT_TOOL_FAMILY
    )
    cases.append(
        _case(
            "mixed_content_and_tool_call_are_separated",
            content == "Checking the registry." and len(calls) == 1,
            {"remaining_content": content, "tool_call_count": len(calls)},
        )
    )

    generic_content, generic_calls = hf_handler.model_specific_tool_parse(
        fenced_final, QWEN3_14B_INSPECT_MODEL_NAME
    )
    cases.append(
        _case(
            "generic_route_reproduces_preflight_failure_mechanism",
            generic_content == "" and generic_calls == [final_json],
            {
                "remaining_content": generic_content,
                "tool_call_count": len(generic_calls),
            },
        )
    )

    implementation = Path("src/provtrust/execution/inspect_compat.py")
    runtime_version = version("inspect_ai")
    passed = (
        info.family == QWEN3_14B_INSPECT_TOOL_FAMILY
        and runtime_version == "0.3.261"
        and all(case["passed"] for case in cases)
    )
    report = {
        "schema_version": "1.0.0",
        "status": "passed" if passed else "failed",
        "purpose": "model-free acceptance of the Inspect/Qwen3 HF tool-parser route",
        "adapter_id": QWEN3_14B_INSPECT_ADAPTER_ID,
        "registration_model_name": QWEN3_14B_INSPECT_MODEL_NAME,
        "model_family": QWEN3_14B_INSPECT_TOOL_FAMILY,
        "runtime": "inspect_ai",
        "runtime_version": runtime_version,
        "implementation_path": implementation.as_posix(),
        "implementation_sha256": sha256_file(implementation),
        "upstream_parser_path": Path(hf_handler.__file__).as_posix(),
        "upstream_parser_sha256": sha256_file(Path(hf_handler.__file__)),
        "cases": cases,
        "scientific_claims_allowed": False,
        "interpretation_boundary": (
            "This artifact validates parser routing only; it makes no claim about "
            "model verification behavior or answer quality."
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
