"""Learn2Discern format adapter; no upstream code is imported or copied."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from provtrust.datasets.io import read_csv


class L2DRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    family_id: str
    question: str
    truth: float
    prior_answer: float | None
    candidate_answer: float
    source_name: str
    source_reliability: float = Field(ge=0.0, le=1.0)
    source_popularity: float | None = Field(default=None, ge=0.0, le=1.0)


DEFAULT_COLUMNS = {
    "item_id": "item_id",
    "family_id": "question_id",
    "question": "question",
    "truth": "truth",
    "prior_answer": "prior_answer",
    "candidate_answer": "candidate_answer",
    "source_name": "source",
    "source_reliability": "reliability",
    "source_popularity": "popularity",
}


def load_l2d_csv(path: Path, columns: dict[str, str] | None = None) -> tuple[L2DRecord, ...]:
    mapping = DEFAULT_COLUMNS | (columns or {})
    records: list[L2DRecord] = []
    for index, row in enumerate(read_csv(path)):
        def value(name: str) -> str:
            column = mapping[name]
            if column not in row:
                raise ValueError(f"missing mapped column {column!r}")
            return row[column]

        prior_raw = value("prior_answer")
        popularity_raw = value("source_popularity")
        payload: dict[str, Any] = {
            "item_id": value("item_id") or f"l2d-{index}",
            "family_id": value("family_id"),
            "question": value("question"),
            "truth": float(value("truth")),
            "prior_answer": float(prior_raw) if prior_raw else None,
            "candidate_answer": float(value("candidate_answer")),
            "source_name": value("source_name"),
            "source_reliability": float(value("source_reliability")),
            "source_popularity": float(popularity_raw) if popularity_raw else None,
        }
        records.append(L2DRecord.model_validate(payload))
    return tuple(records)


def improvement_toward_truth(record: L2DRecord) -> float | None:
    if record.prior_answer is None:
        return None
    return abs(record.prior_answer - record.truth) - abs(record.candidate_answer - record.truth)
