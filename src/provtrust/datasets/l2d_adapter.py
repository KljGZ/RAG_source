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


def _mapped_value(row: dict[str, str], mapping: dict[str, str], name: str) -> str:
    column = mapping[name]
    if column not in row:
        raise ValueError(f"missing mapped column {column!r}")
    return row[column]


def load_l2d_csv(path: Path, columns: dict[str, str] | None = None) -> tuple[L2DRecord, ...]:
    mapping = DEFAULT_COLUMNS | (columns or {})
    records: list[L2DRecord] = []
    for index, row in enumerate(read_csv(path)):
        prior_raw = _mapped_value(row, mapping, "prior_answer")
        popularity_raw = _mapped_value(row, mapping, "source_popularity")
        payload: dict[str, Any] = {
            "item_id": _mapped_value(row, mapping, "item_id") or f"l2d-{index}",
            "family_id": _mapped_value(row, mapping, "family_id"),
            "question": _mapped_value(row, mapping, "question"),
            "truth": float(_mapped_value(row, mapping, "truth")),
            "prior_answer": float(prior_raw) if prior_raw else None,
            "candidate_answer": float(_mapped_value(row, mapping, "candidate_answer")),
            "source_name": _mapped_value(row, mapping, "source_name"),
            "source_reliability": float(_mapped_value(row, mapping, "source_reliability")),
            "source_popularity": float(popularity_raw) if popularity_raw else None,
        }
        records.append(L2DRecord.model_validate(payload))
    return tuple(records)


def improvement_toward_truth(record: L2DRecord) -> float | None:
    if record.prior_answer is None:
        return None
    return abs(record.prior_answer - record.truth) - abs(record.candidate_answer - record.truth)
