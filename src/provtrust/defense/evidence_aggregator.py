"""Aggregate evidence by independent roots with authority non-amplification."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field


class EvidenceContribution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str
    root_id: str
    identity_authentic: float = Field(ge=0.0, le=1.0)
    attribution_authentic: float = Field(ge=0.0, le=1.0)
    warrant: float = Field(ge=-1.0, le=1.0)
    claim_conditioned_reliability: float = Field(ge=0.0, le=1.0)
    independence: float = Field(default=1.0, ge=0.0, le=1.0)
    verified_root_reliability: float | None = Field(default=None, ge=0.0, le=1.0)


class RootContribution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    root_id: str
    weight: float
    evidence_ids: tuple[str, ...]
    effective_reliability: float


class AggregatedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    root_contributions: tuple[RootContribution, ...]
    support: float
    contradiction: float
    unresolved_conflict: bool


def aggregate_by_root(
    contributions: tuple[EvidenceContribution, ...], *, conflict_threshold: float = 0.15
) -> AggregatedEvidence:
    grouped: dict[str, list[EvidenceContribution]] = defaultdict(list)
    for contribution in contributions:
        grouped[contribution.root_id].append(contribution)
    roots: list[RootContribution] = []
    for root_id in sorted(grouped):
        group = grouped[root_id]
        verified_reliabilities = [
            value.verified_root_reliability
            for value in group
            if value.verified_root_reliability is not None
        ]
        ceiling = max(verified_reliabilities) if verified_reliabilities else 0.0
        proposed = max(value.claim_conditioned_reliability for value in group)
        effective_reliability = min(proposed, ceiling)
        # Multiple copies under one root do not add linearly. Keep only the
        # strongest absolute warranted contribution for that independent root.
        candidate_weights = [
            value.identity_authentic
            * value.attribution_authentic
            * value.warrant
            * effective_reliability
            * value.independence
            for value in group
        ]
        weight = max(candidate_weights, key=abs)
        roots.append(
            RootContribution(
                root_id=root_id,
                weight=weight,
                evidence_ids=tuple(sorted(value.evidence_id for value in group)),
                effective_reliability=effective_reliability,
            )
        )
    support = sum(max(root.weight, 0.0) for root in roots)
    contradiction = sum(max(-root.weight, 0.0) for root in roots)
    return AggregatedEvidence(
        root_contributions=tuple(roots),
        support=support,
        contradiction=contradiction,
        unresolved_conflict=support >= conflict_threshold and contradiction >= conflict_threshold,
    )
