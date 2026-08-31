"""Deterministic primary metrics and optional external-evaluator adapters."""

from provtrust.scorers.attribution import attribution_authenticity_gap
from provtrust.scorers.belief_update import directed_claim_adoption, normalized_claim_adoption
from provtrust.scorers.calibration import brier_score, expected_calibration_error
from provtrust.scorers.independence import consensus_laundering_amplification
from provtrust.scorers.rationale import rationale_causal_consistency
from provtrust.scorers.source_sensitivity import normative_factor_control_ratio
from provtrust.scorers.tool_trace import verification_completed
from provtrust.scorers.warrant import warrant_monotonicity_violation_rate

__all__ = [
    "attribution_authenticity_gap",
    "brier_score",
    "consensus_laundering_amplification",
    "directed_claim_adoption",
    "expected_calibration_error",
    "normalized_claim_adoption",
    "normative_factor_control_ratio",
    "rationale_causal_consistency",
    "verification_completed",
    "warrant_monotonicity_violation_rate",
]
