"""Frozen estimands for exploratory interactive-verification results."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from statistics import median
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from provtrust.analysis.bootstrap import cluster_bootstrap_mean
from provtrust.analysis.randomization_test import sign_flip_randomization_test


class InteractiveObservation(BaseModel):
    """One redacted, analysis-ready Track E observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    family_id: str
    event_id: str
    root_claim_id: str
    paired_scene_id: str
    model_id: str
    policy: str
    scenario: str
    risk: Literal["low", "high"]
    parse_success: bool
    parse_mode_prior: str | None = None
    parse_mode_posterior: str | None = None
    prior_answer: bool | str | float | None = None
    prior_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    prior_abstained: bool | None = None
    posterior_answer: bool | str | float | None = None
    posterior_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    posterior_abstained: bool | None = None
    claimed_verified: bool | None = None
    prior_answer_type_valid: bool | None = None
    posterior_answer_type_valid: bool | None = None
    citation_valid: bool | None = None
    claim_adoption_shift: float | None = None
    correct: bool | None = None
    false_verification_assurance: bool | None = None
    triggered: bool
    completed: bool
    verification_components: dict[str, bool]
    missing_components: tuple[str, ...]
    tool_call_count: int = Field(ge=0)
    successful_tool_call_count: int = Field(ge=0)
    failed_tool_call_count: int = Field(ge=0)
    tool_calls: tuple[dict[str, Any], ...]
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    turn_count: int = Field(ge=0)
    total_time_seconds: float = Field(ge=0.0)
    error_retries: int = Field(ge=0)
    sample_error: str | None = None

    @property
    def confidence_change(self) -> float | None:
        if self.prior_confidence is None or self.posterior_confidence is None:
            return None
        return self.posterior_confidence - self.prior_confidence


def wilson_rate(values: Sequence[bool | None]) -> dict[str, float | int | None]:
    """Return a Wilson interval while preserving the missing denominator."""

    observed = [value for value in values if value is not None]
    missing = len(values) - len(observed)
    if not observed:
        return {
            "numerator": 0,
            "denominator": 0,
            "missing": missing,
            "rate": None,
            "ci95_lower": None,
            "ci95_upper": None,
        }
    successes = sum(observed)
    count = len(observed)
    estimate = successes / count
    z = 1.959963984540054
    denominator = 1.0 + z * z / count
    centre = (estimate + z * z / (2.0 * count)) / denominator
    half_width = (
        z
        * math.sqrt(estimate * (1.0 - estimate) / count + z * z / (4.0 * count * count))
        / denominator
    )
    return {
        "numerator": successes,
        "denominator": count,
        "missing": missing,
        "rate": estimate,
        "ci95_lower": max(0.0, centre - half_width),
        "ci95_upper": min(1.0, centre + half_width),
    }


def exact_discordant_p(positive: int, negative: int) -> float:
    """Two-sided exact paired-binomial p-value for discordant binary pairs."""

    if positive < 0 or negative < 0:
        raise ValueError("discordant counts must be non-negative")
    total = positive + negative
    if total == 0:
        return 1.0
    tail = sum(math.comb(total, index) for index in range(min(positive, negative) + 1))
    return float(min(1.0, 2.0 * tail / (2**total)))


def _outcome_value(observation: InteractiveObservation, outcome: str) -> bool | float | None:
    if outcome == "confidence_change":
        return observation.confidence_change
    value = getattr(observation, outcome)
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    raise TypeError(f"unsupported paired outcome: {outcome}")


def paired_contrast(
    observations: Sequence[InteractiveObservation],
    *,
    contrast_id: str,
    outcome: str,
    level_field: Literal["risk", "policy"],
    left_level: str,
    right_level: str,
    pair_key_fields: tuple[str, ...],
    seed: int,
) -> dict[str, Any]:
    """Estimate a right-minus-left contrast with family-clustered uncertainty."""

    grouped: dict[tuple[str, ...], dict[str, InteractiveObservation]] = defaultdict(dict)
    for observation in observations:
        level = str(getattr(observation, level_field))
        if level not in {left_level, right_level}:
            continue
        key = tuple(str(getattr(observation, field)) for field in pair_key_fields)
        if level in grouped[key]:
            raise ValueError(f"duplicate level within matched pair: {contrast_id}:{key}:{level}")
        grouped[key][level] = observation

    differences: list[float] = []
    cluster_values: dict[str, list[float]] = defaultdict(list)
    incomplete_pairs = 0
    missing_outcome_pairs = 0
    positive_discordant = 0
    negative_discordant = 0
    binary = True
    for levels in grouped.values():
        if set(levels) != {left_level, right_level}:
            incomplete_pairs += 1
            continue
        left_observation = levels[left_level]
        right_observation = levels[right_level]
        left = _outcome_value(left_observation, outcome)
        right = _outcome_value(right_observation, outcome)
        if left is None or right is None:
            missing_outcome_pairs += 1
            continue
        binary = binary and isinstance(left, bool) and isinstance(right, bool)
        difference = float(right) - float(left)
        differences.append(difference)
        cluster_values[left_observation.family_id].append(difference)
        if isinstance(left, bool) and isinstance(right, bool):
            positive_discordant += int(not left and right)
            negative_discordant += int(left and not right)

    if not differences:
        return {
            "contrast_id": contrast_id,
            "outcome": outcome,
            "estimand": f"{right_level}_minus_{left_level}",
            "pair_key_fields": list(pair_key_fields),
            "matched_pair_count": 0,
            "incomplete_pair_count": incomplete_pairs,
            "missing_outcome_pair_count": missing_outcome_pairs,
            "family_cluster_count": 0,
            "estimate": None,
            "pair_weighted_estimate": None,
            "median_pair_difference": None,
            "ci95_lower": None,
            "ci95_upper": None,
            "bootstrap_replicates": 0,
            "cluster_sign_flip_p_two_sided": None,
            "cluster_sign_flip_exact": None,
            "cluster_sign_flip_permutations": 0,
            "binary_discordant_right_positive": None,
            "binary_discordant_left_positive": None,
            "binary_exact_p_two_sided": None,
        }

    frozen_clusters = {family: tuple(values) for family, values in sorted(cluster_values.items())}
    bootstrap = cluster_bootstrap_mean(frozen_clusters, seed=seed)
    family_means = tuple(sum(values) / len(values) for values in frozen_clusters.values())
    sign_flip = sign_flip_randomization_test(family_means, seed=seed)
    return {
        "contrast_id": contrast_id,
        "outcome": outcome,
        "estimand": f"{right_level}_minus_{left_level}",
        "pair_key_fields": list(pair_key_fields),
        "matched_pair_count": len(differences),
        "incomplete_pair_count": incomplete_pairs,
        "missing_outcome_pair_count": missing_outcome_pairs,
        "family_cluster_count": len(frozen_clusters),
        "estimate": bootstrap.estimate,
        "pair_weighted_estimate": sum(differences) / len(differences),
        "median_pair_difference": median(differences),
        "ci95_lower": bootstrap.lower,
        "ci95_upper": bootstrap.upper,
        "bootstrap_replicates": bootstrap.replicates,
        "cluster_sign_flip_p_two_sided": sign_flip.p_value_two_sided,
        "cluster_sign_flip_exact": sign_flip.exact,
        "cluster_sign_flip_permutations": sign_flip.permutations,
        "binary_discordant_right_positive": positive_discordant if binary else None,
        "binary_discordant_left_positive": negative_discordant if binary else None,
        "binary_exact_p_two_sided": (
            exact_discordant_p(positive_discordant, negative_discordant) if binary else None
        ),
    }


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    """Holm adjustment with monotonicity in ascending raw-p order."""

    ordered = sorted(p_values, key=lambda key: (p_values[key], key))
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for index, key in enumerate(ordered):
        running = max(running, min(1.0, (total - index) * p_values[key]))
        adjusted[key] = running
    return adjusted
