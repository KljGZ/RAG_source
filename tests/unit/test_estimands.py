from __future__ import annotations

from provtrust.analysis.estimands import FactorObservation, matched_factor_effects


def test_matched_factor_effect_holds_other_factors_fixed() -> None:
    observations = (
        FactorObservation(
            item_id="a",
            family_id="f",
            model_id="m",
            factors={"attribution": False, "style": "low"},
            value=0.2,
        ),
        FactorObservation(
            item_id="b",
            family_id="f",
            model_id="m",
            factors={"attribution": True, "style": "low"},
            value=0.8,
        ),
        FactorObservation(
            item_id="c",
            family_id="f",
            model_id="m",
            factors={"attribution": True, "style": "high"},
            value=0.9,
        ),
    )
    effects = matched_factor_effects(
        observations, factor="attribution", treated=True, control=False
    )
    assert len(effects) == 1
    assert effects[0].effect == 0.6
