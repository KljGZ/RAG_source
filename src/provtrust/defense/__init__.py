"""Provenance-Aware Verification Gate (PAVG)."""

from provtrust.defense.abstention import AbstentionDecision, decide_abstention
from provtrust.defense.evidence_aggregator import AggregatedEvidence, aggregate_by_root
from provtrust.defense.pavg_agent import PAVGAgent, PAVGInput, PAVGResult
from provtrust.defense.risk_gate import RiskAssessment, RiskGate, RiskWeights

__all__ = [
    "AbstentionDecision",
    "AggregatedEvidence",
    "PAVGAgent",
    "PAVGInput",
    "PAVGResult",
    "RiskAssessment",
    "RiskGate",
    "RiskWeights",
    "aggregate_by_root",
    "decide_abstention",
]
