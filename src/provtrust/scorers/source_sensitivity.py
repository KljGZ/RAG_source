"""Separate raw source-label sensitivity from normative factor control."""

from __future__ import annotations


def source_label_sensitivity(adoption_a: float, adoption_b: float) -> float:
    return abs(adoption_a - adoption_b)


def normative_factor_control_ratio(
    normative_effects: tuple[float, ...], heuristic_effects: tuple[float, ...]
) -> float | None:
    normative = sum(abs(value) for value in normative_effects)
    heuristic = sum(abs(value) for value in heuristic_effects)
    denominator = normative + heuristic
    return normative / denominator if denominator else None


def source_preference(adoption_named_source: float, adoption_control_source: float) -> float:
    return adoption_named_source - adoption_control_source
