from __future__ import annotations

import pytest

from provtrust.scorers.belief_update import normalized_claim_adoption
from provtrust.scorers.independence import consensus_laundering_amplification
from provtrust.scorers.rationale import rationale_causal_consistency
from provtrust.scorers.source_sensitivity import normative_factor_control_ratio
from provtrust.scorers.warrant import warrant_monotonicity_violation_rate
from provtrust.schemas.evidence import WarrantLevel


def test_normalized_adoption_is_not_clipped() -> None:
    assert normalized_claim_adoption(0.0, 1.5, 1.0) == pytest.approx(1.5)
    assert normalized_claim_adoption(0.0, -0.5, 1.0) == pytest.approx(-0.5)


def test_warrant_violation_rate() -> None:
    values = {
        WarrantLevel.UNSUPPORTED: 0.2,
        WarrantLevel.RELATED_ONLY: 0.1,
        WarrantLevel.DIRECT_SUPPORT: 0.8,
    }
    assert warrant_monotonicity_violation_rate(values) == pytest.approx(0.5)


def test_normative_control_ratio() -> None:
    assert normative_factor_control_ratio((2.0,), (1.0, 1.0)) == pytest.approx(0.5)
    assert consensus_laundering_amplification(0.7, 0.4) == pytest.approx(0.3)


def test_rationale_consistency_uses_counterfactuals() -> None:
    result = rationale_causal_consistency(
        {"attribution": 2.0, "style": -1.0}, {"attribution": 0.4, "style": -0.1}
    )
    assert result["sign_agreement"] == 1.0
    assert result["spearman"] == pytest.approx(1.0)
