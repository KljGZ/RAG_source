from __future__ import annotations

import pytest

from provtrust.analysis.static_results import StaticObservation, compute_static_contrasts


def _observation(
    *, cell: str, factor: str | None, control: str | None, adoption: float
) -> StaticObservation:
    return StaticObservation(
        item_id=f"item-{cell}",
        family_id="family-1",
        model_id="model-1",
        design_cell_id=cell,
        contrast_factor=factor,
        control_cell_id=control,
        claim_truth=True,
        gold_answer=True,
        candidate_answer=True,
        factors={"claim_conditioned_reliability": 0.8},
        parse_success=True,
        prior_answer=None,
        prior_confidence=0.0,
        prior_abstained=True,
        prior_answer_type_valid=True,
        posterior_answer=True,
        posterior_confidence=0.8,
        posterior_abstained=False,
        posterior_answer_type_valid=True,
        claim_adoption_shift=adoption,
        correct=True,
        citation_valid=True,
        claimed_verified=False,
        verification_completed=False,
        false_verification_assurance=False,
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        total_time_seconds=1.0,
    )


def test_static_contrast_orients_normative_low_vs_high() -> None:
    baseline = _observation(cell="baseline", factor=None, control=None, adoption=0.8)
    low = _observation(
        cell="reliability_low",
        factor="claim_conditioned_reliability",
        control="baseline",
        adoption=0.2,
    )

    effects = compute_static_contrasts((baseline, low))

    assert len(effects) == 1
    assert effects[0].raw_adoption_effect == pytest.approx(-0.6)
    assert effects[0].normative_oriented_effect == pytest.approx(0.6)
    assert effects[0].factor_class == "normative"
