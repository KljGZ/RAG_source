"""Neutral adapter for local GroupQA-style multi-document conflict sets."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from provtrust.datasets.io import read_jsonl


class ConflictDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    text: str = Field(min_length=1)
    answer: str
    source_id: str | None = None
    provenance_root_id: str | None = None


class ConflictSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    family_id: str
    question: str
    gold_answer: str
    documents: tuple[ConflictDocument, ...]


def load_groupqa_jsonl(path: Path) -> tuple[ConflictSet, ...]:
    return tuple(ConflictSet.model_validate(row) for row in read_jsonl(path))
