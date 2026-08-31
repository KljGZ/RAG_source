"""Calibrated abstention policy for unresolved or unverified evidence."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from provtrust.defense.evidence_aggregator import AggregatedEvidence


class AbstentionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    abstain: bool
    reason: str | None
    confidence: float


def decide_abstention(
    aggregate: AggregatedEvidence,
    *,
    verification_required: bool,
    verification_completed: bool,
    minimum_margin: float = 0.2,
) -> AbstentionDecision:
    if verification_required and not verification_completed:
        return AbstentionDecision(
            abstain=True, reason="required_verification_incomplete", confidence=0.0
        )
    if aggregate.unresolved_conflict:
        return AbstentionDecision(abstain=True, reason="unresolved_evidence_conflict", confidence=0.0)
    total = aggregate.support + aggregate.contradiction
    margin = abs(aggregate.support - aggregate.contradiction)
    if total == 0.0 or margin < minimum_margin:
        return AbstentionDecision(abstain=True, reason="insufficient_verified_evidence", confidence=0.0)
    return AbstentionDecision(abstain=False, reason=None, confidence=min(margin / total, 1.0))
