"""Directed belief-update estimands."""

from __future__ import annotations

import math


def directed_claim_adoption(prior: float, posterior: float, candidate: float) -> float:
    """Signed movement toward the candidate claim in answer units."""

    direction = math.copysign(1.0, candidate - prior) if candidate != prior else 0.0
    return (posterior - prior) * direction


def normalized_claim_adoption(prior: float, posterior: float, candidate: float) -> float | None:
    """Movement toward the candidate divided by the prior-candidate distance.

    Values may exceed one or be negative; primary analyses must not clip them.
    """

    distance = abs(candidate - prior)
    if distance == 0.0:
        return None
    return directed_claim_adoption(prior, posterior, candidate) / distance


def truth_improvement(prior: float, posterior: float, truth: float) -> float:
    return abs(prior - truth) - abs(posterior - truth)
