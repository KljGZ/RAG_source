"""Composable PAVG decision pipeline."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from provtrust.defense.abstention import AbstentionDecision, decide_abstention
from provtrust.defense.evidence_aggregator import (
    AggregatedEvidence,
    EvidenceContribution,
    aggregate_by_root,
)
from provtrust.defense.risk_gate import RiskAssessment, RiskFeatures, RiskGate, RiskWeights


class PAVGInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    risk_features: RiskFeatures
    contributions: tuple[EvidenceContribution, ...]
    verification_completed: bool


class PAVGResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    risk: RiskAssessment
    aggregate: AggregatedEvidence
    decision: AbstentionDecision
    answer_polarity: str


class PAVGAgent:
    def __init__(self, risk_weights: RiskWeights) -> None:
        self.risk_gate = RiskGate(risk_weights)

    def evaluate(self, value: PAVGInput) -> PAVGResult:
        risk = self.risk_gate.assess(value.risk_features)
        aggregate = aggregate_by_root(value.contributions)
        decision = decide_abstention(
            aggregate,
            verification_required=risk.verification_required,
            verification_completed=value.verification_completed,
        )
        if decision.abstain:
            polarity = "abstain"
        elif aggregate.support > aggregate.contradiction:
            polarity = "support"
        else:
            polarity = "contradict"
        return PAVGResult(
            risk=risk, aggregate=aggregate, decision=decision, answer_polarity=polarity
        )
