"""Causal faithfulness of declared factors, without hidden chain-of-thought."""

from __future__ import annotations

import math
from collections.abc import Mapping

from scipy.stats import spearmanr  # type: ignore[import-untyped]


def rationale_causal_consistency(
    declared_weights: Mapping[str, float], causal_effects: Mapping[str, float]
) -> dict[str, float | int | None]:
    common = sorted(set(declared_weights) & set(causal_effects))
    if not common:
        return {"factor_count": 0, "spearman": None, "sign_agreement": None, "cosine": None}
    declared = [declared_weights[name] for name in common]
    causal = [causal_effects[name] for name in common]
    if len(common) < 2 or len(set(declared)) == 1 or len(set(causal)) == 1:
        correlation: float | None = None
    else:
        value = float(spearmanr(declared, causal).statistic)
        correlation = None if math.isnan(value) else value
    sign_agreement = sum(
        (left == 0.0 and right == 0.0) or (left * right > 0.0)
        for left, right in zip(declared, causal)
    ) / len(common)
    norm_declared = math.sqrt(sum(value * value for value in declared))
    norm_causal = math.sqrt(sum(value * value for value in causal))
    cosine = (
        sum(left * right for left, right in zip(declared, causal))
        / (norm_declared * norm_causal)
        if norm_declared and norm_causal
        else None
    )
    return {
        "factor_count": len(common),
        "spearman": correlation,
        "sign_agreement": sign_agreement,
        "cosine": cosine,
    }
