"""Connected-component split assignment across every leakage grouping key."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from provtrust.schemas.trial import Trial


@dataclass(frozen=True)
class SplitAssignment:
    item_id: str
    component_id: str
    split: str


class _UnionFind:
    def __init__(self, values: list[str]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[max(left_root, right_root)] = min(left_root, right_root)


def _bucket(component: str, seed: int) -> float:
    digest = hashlib.sha256(f"{seed}:{component}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


def assign_grouped_splits(
    trials: tuple[Trial, ...],
    *,
    seed: int,
    train_fraction: float = 0.7,
    validation_fraction: float = 0.15,
) -> tuple[SplitAssignment, ...]:
    if not 0.0 <= train_fraction <= 1.0:
        raise ValueError("train_fraction must be within [0, 1]")
    if not 0.0 <= validation_fraction <= 1.0:
        raise ValueError("validation_fraction must be within [0, 1]")
    if train_fraction + validation_fraction > 1.0:
        raise ValueError("split fractions exceed one")
    item_ids = [trial.item_id for trial in trials]
    union_find = _UnionFind(item_ids)
    observed: dict[tuple[str, str], str] = {}
    for trial in trials:
        groups = {
            ("family", trial.family_id),
            ("root_claim", trial.root_claim_id),
        }
        if trial.event_id is not None:
            groups.add(("event", trial.event_id))
        for group in groups:
            if group in observed:
                union_find.union(trial.item_id, observed[group])
            else:
                observed[group] = trial.item_id
    assignments: list[SplitAssignment] = []
    for item_id in sorted(item_ids):
        component = union_find.find(item_id)
        value = _bucket(component, seed)
        if value < train_fraction:
            split = "train"
        elif value < train_fraction + validation_fraction:
            split = "validation"
        else:
            split = "test"
        assignments.append(SplitAssignment(item_id, component, split))
    return tuple(assignments)
