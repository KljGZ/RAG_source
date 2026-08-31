"""Paired estimands defined before model fitting."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, ConfigDict


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    family_id: str
    condition: str
    value: float


class PairedEffect(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    family_id: str
    treated_condition: str
    control_condition: str
    treated_mean: float
    control_mean: float
    effect: float


def paired_family_effects(
    observations: tuple[Observation, ...], *, treated: str, control: str
) -> tuple[PairedEffect, ...]:
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for observation in observations:
        grouped[observation.family_id][observation.condition].append(observation.value)
    effects: list[PairedEffect] = []
    for family_id in sorted(grouped):
        family = grouped[family_id]
        if treated not in family or control not in family:
            continue
        treated_mean = sum(family[treated]) / len(family[treated])
        control_mean = sum(family[control]) / len(family[control])
        effects.append(
            PairedEffect(
                family_id=family_id,
                treated_condition=treated,
                control_condition=control,
                treated_mean=treated_mean,
                control_mean=control_mean,
                effect=treated_mean - control_mean,
            )
        )
    return tuple(effects)
