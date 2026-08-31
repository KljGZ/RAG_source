"""Adapter for the claim-truth by citation-truth factorial design."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from provtrust.datasets.io import read_jsonl


class AuthorityRecord(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    item_id: str
    family_id: str
    claim: str
    claim_truth: bool
    citation: str
    citation_truth: bool


def load_authoritybench_jsonl(path: Path) -> tuple[AuthorityRecord, ...]:
    return tuple(AuthorityRecord.model_validate(row) for row in read_jsonl(path))
