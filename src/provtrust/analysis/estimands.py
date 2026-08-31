"""Paired estimands defined before model fitting."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

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


class FactorObservation(BaseModel):
    """One outcome with all randomized/intervened factors made explicit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    family_id: str
    model_id: str
    factors: dict[str, bool | float | int | str]
    value: float


class MatchedFactorEffect(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    family_id: str
    model_id: str
    factor: str
    treated_level: bool | float | int | str
    control_level: bool | float | int | str
    stratum: str
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


def matched_factor_effects(
    observations: tuple[FactorObservation, ...],
    *,
    factor: str,
    treated: bool | float | int | str,
    control: bool | float | int | str,
) -> tuple[MatchedFactorEffect, ...]:
    """Compute exact matched contrasts while holding all other factors fixed."""

    grouped: dict[tuple[str, str, str], dict[bool | float | int | str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for observation in observations:
        if factor not in observation.factors:
            raise KeyError(f"factor missing from observation: {factor}")
        level = observation.factors[factor]
        if level not in {treated, control}:
            continue
        controls: dict[str, Any] = {
            name: value for name, value in observation.factors.items() if name != factor
        }
        stratum = json.dumps(controls, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        grouped[(observation.family_id, observation.model_id, stratum)][level].append(
            observation.value
        )
    effects: list[MatchedFactorEffect] = []
    for (family_id, model_id, stratum), levels in sorted(grouped.items()):
        if treated not in levels or control not in levels:
            continue
        treated_mean = sum(levels[treated]) / len(levels[treated])
        control_mean = sum(levels[control]) / len(levels[control])
        effects.append(
            MatchedFactorEffect(
                family_id=family_id,
                model_id=model_id,
                factor=factor,
                treated_level=treated,
                control_level=control,
                stratum=stratum,
                treated_mean=treated_mean,
                control_mean=control_mean,
                effect=treated_mean - control_mean,
            )
        )
    return tuple(effects)
