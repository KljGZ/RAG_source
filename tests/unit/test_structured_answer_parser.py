from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from provtrust.tasks.common import parse_structured_answer


def _payload() -> str:
    return json.dumps(
        {
            "answer": True,
            "confidence": 0.75,
            "abstained": False,
            "claimed_verified": False,
            "cited_evidence_ids": ["evidence-1"],
            "declared_factors": {"warrant": 1.0},
        }
    )


def test_structured_answer_parser_accepts_raw_json() -> None:
    answer, mode = parse_structured_answer(_payload())
    assert answer.answer is True
    assert mode == "raw_json"


def test_structured_answer_parser_accepts_one_whole_json_fence() -> None:
    answer, mode = parse_structured_answer(f"```json\n{_payload()}\n```")
    assert answer.answer is True
    assert mode == "single_json_code_fence"


@pytest.mark.parametrize("closing_fence", ["```", "``` "])
def test_structured_answer_parser_accepts_registered_explanation_wrapper(
    closing_fence: str,
) -> None:
    response = (
        f"```json\n{_payload()}\n{closing_fence}\n\n"
        "Explanation: Concise public rationale for the structured fields."
    )

    answer, mode = parse_structured_answer(response)

    assert answer.answer is True
    assert mode == "leading_json_code_fence_with_explanation"


@pytest.mark.parametrize(
    "response",
    [
        lambda: f"Here is the answer:\n```json\n{_payload()}\n```",
        lambda: f"```json\n{_payload()}\n```\nAdditional text",
        lambda: f"```json\n{_payload()}\n```\n\nExplanation:",
        lambda: (
            f"```json\n{_payload()}\n```\n\nExplanation: rationale\n"
            f"```json\n{_payload()}\n```"
        ),
        lambda: f"```\n{_payload()}\n```",
        lambda: f"```json\n{_payload()}\n```\n```json\n{_payload()}\n```",
    ],
)
def test_structured_answer_parser_rejects_noncanonical_wrappers(response: object) -> None:
    assert callable(response)
    with pytest.raises(ValidationError):
        parse_structured_answer(response())
