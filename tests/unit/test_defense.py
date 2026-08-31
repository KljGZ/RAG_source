from __future__ import annotations

from provtrust.defense.evidence_aggregator import EvidenceContribution, aggregate_by_root
from provtrust.defense.pavg_agent import PAVGAgent, PAVGInput
from provtrust.defense.risk_gate import RiskFeatures, RiskWeights


def contribution(evidence_id: str, root_id: str, warrant: float = 1.0) -> EvidenceContribution:
    return EvidenceContribution(
        evidence_id=evidence_id,
        root_id=root_id,
        identity_authentic=1.0,
        attribution_authentic=1.0,
        warrant=warrant,
        claim_conditioned_reliability=0.9,
        verified_root_reliability=0.7,
    )


def test_duplicate_root_is_idempotent() -> None:
    single = aggregate_by_root((contribution("e1", "r1"),))
    duplicate = aggregate_by_root(
        (contribution("e1", "r1"), contribution("e2", "r1"))
    )
    assert duplicate.support == single.support
    assert duplicate.root_contributions[0].effective_reliability == 0.7


def test_unverified_authority_cannot_amplify() -> None:
    value = EvidenceContribution(
        evidence_id="e",
        root_id="r",
        identity_authentic=1.0,
        attribution_authentic=1.0,
        warrant=1.0,
        claim_conditioned_reliability=1.0,
        verified_root_reliability=None,
    )
    assert aggregate_by_root((value,)).support == 0.0


def test_high_risk_requires_completed_verification() -> None:
    agent = PAVGAgent(RiskWeights(threshold=0.5))
    result = agent.evaluate(
        PAVGInput(
            risk_features=RiskFeatures(
                conflict=1.0,
                unfamiliarity=0.0,
                high_stakes=1.0,
                attribution_anomaly=0.0,
                source_dependence=0.0,
                prior_conflict=0.0,
            ),
            contributions=(contribution("e1", "r1"),),
            verification_completed=False,
        )
    )
    assert result.decision.abstain
    assert result.decision.reason == "required_verification_incomplete"
