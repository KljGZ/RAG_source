"""Locate literal evidence spans without making an entailment judgment."""

from __future__ import annotations

import json
import re
from pydantic import BaseModel, ConfigDict, Field
from inspect_ai.tool import Tool, tool


class EvidenceMatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str


def find_evidence_spans(document: str, needle: str, *, ignore_case: bool = True) -> tuple[EvidenceMatch, ...]:
    if not needle:
        raise ValueError("evidence needle must not be empty")
    flags = re.IGNORECASE if ignore_case else 0
    return tuple(
        EvidenceMatch(start=match.start(), end=match.end(), text=match.group(0))
        for match in re.finditer(re.escape(needle), document, flags)
    )


@tool(parallel=True)
def find_evidence() -> Tool:
    async def execute(document: str, needle: str, ignore_case: bool = True) -> str:
        """Find literal supporting-text candidates in a supplied snapshot.

        Args:
            document: Snapshot text to inspect.
            needle: Exact phrase to locate.
            ignore_case: Whether matching ignores case.

        Returns:
            JSON character spans; these are not themselves entailment labels.
        """

        matches = find_evidence_spans(document, needle, ignore_case=ignore_case)
        return json.dumps([match.model_dump() for match in matches], ensure_ascii=False)

    return execute
