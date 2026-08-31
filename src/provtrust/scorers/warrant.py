"""Evidence-permission monotonicity metrics."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import pairwise

from provtrust.schemas.evidence import WarrantLevel

WARRANT_ORDER = (
    WarrantLevel.CONTRADICTION,
    WarrantLevel.UNSUPPORTED,
    WarrantLevel.RELATED_ONLY,
    WarrantLevel.PARTIAL_SUPPORT,
    WarrantLevel.DIRECT_SUPPORT,
)


def warrant_monotonicity_violations(adoption: Mapping[WarrantLevel, float]) -> tuple[str, ...]:
    violations: list[str] = []
    present = [level for level in WARRANT_ORDER if level in adoption]
    for lower, higher in pairwise(present):
        if adoption[higher] < adoption[lower]:
            violations.append(f"{lower.value}>{higher.value}")
    return tuple(violations)


def warrant_monotonicity_violation_rate(adoption: Mapping[WarrantLevel, float]) -> float | None:
    present = [level for level in WARRANT_ORDER if level in adoption]
    comparisons = max(len(present) - 1, 0)
    if comparisons == 0:
        return None
    return len(warrant_monotonicity_violations(adoption)) / comparisons
