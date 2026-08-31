"""Dataset invariants and split-leakage audit."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from provtrust.datasets.split import SplitAssignment
from provtrust.schemas.trial import Trial


class DatasetAudit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    item_count: int
    family_count: int
    event_count: int
    root_claim_count: int
    condition_counts: dict[str, int]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def validate_trials(
    trials: tuple[Trial, ...], assignments: tuple[SplitAssignment, ...] | None = None
) -> DatasetAudit:
    errors: list[str] = []
    warnings: list[str] = []
    ids = [trial.item_id for trial in trials]
    duplicates = sorted(item_id for item_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate item_id values: {duplicates[:10]}")
    family_conditions: dict[str, set[str]] = defaultdict(set)
    condition_counts: Counter[str] = Counter()
    for trial in trials:
        family_conditions[trial.family_id].add(trial.intervention)
        condition_counts[trial.intervention] += 1
        if trial.claim_conditioned_reliability is None:
            warnings.append(f"{trial.item_id}: claim-conditioned reliability is unknown")
    if assignments is not None:
        assignment_map = {entry.item_id: entry.split for entry in assignments}
        if set(assignment_map) != set(ids):
            errors.append("split assignments do not match trial item identifiers")
        grouping_keys: tuple[tuple[str, Callable[[Trial], str | None]], ...] = (
            ("family_id", lambda trial: trial.family_id),
            ("root_claim_id", lambda trial: trial.root_claim_id),
            ("event_id", lambda trial: trial.event_id),
        )
        for key_name, key in grouping_keys:
            grouped: dict[str, set[str]] = defaultdict(set)
            for trial in trials:
                value = key(trial)
                if value is not None and trial.item_id in assignment_map:
                    grouped[value].add(assignment_map[trial.item_id])
            leaked = sorted(value for value, splits in grouped.items() if len(splits) > 1)
            if leaked:
                errors.append(f"{key_name} leaks across splits: {leaked[:10]}")
    return DatasetAudit(
        item_count=len(trials),
        family_count=len({trial.family_id for trial in trials}),
        event_count=len({trial.event_id for trial in trials if trial.event_id is not None}),
        root_claim_count=len({trial.root_claim_id for trial in trials}),
        condition_counts=dict(sorted(condition_counts.items())),
        errors=tuple(errors),
        warnings=tuple(dict.fromkeys(warnings)),
    )
