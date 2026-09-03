from __future__ import annotations

import pytest

from provtrust.analysis.interactive_results import (
    InteractiveObservation,
    exact_discordant_p,
    holm_adjust,
    paired_contrast,
    wilson_rate,
)


def _observation(
    family: str,
    risk: str,
    *,
    triggered: bool,
    posterior_confidence: float | None = 0.5,
) -> InteractiveObservation:
    return InteractiveObservation(
        item_id=f"{family}-{risk}",
        family_id=family,
        event_id=f"{family}-event",
        root_claim_id=f"{family}-root",
        paired_scene_id=f"{family}-scene",
        model_id="model",
        policy="tools_unprompted",
        scenario="c1_authentic_direct",
        risk=risk,
        parse_success=posterior_confidence is not None,
        prior_confidence=0.25 if posterior_confidence is not None else None,
        posterior_confidence=posterior_confidence,
        triggered=triggered,
        completed=False,
        verification_components={"component": False},
        missing_components=("component",),
        tool_call_count=int(triggered),
        successful_tool_call_count=int(triggered),
        failed_tool_call_count=0,
        tool_calls=(),
        input_tokens=1,
        output_tokens=1,
        total_tokens=2,
        turn_count=2,
        total_time_seconds=1.0,
        error_retries=0,
    )


def test_wilson_rate_preserves_missing_denominator() -> None:
    result = wilson_rate([True, False, None, True])

    assert result["numerator"] == 2
    assert result["denominator"] == 3
    assert result["missing"] == 1
    assert result["rate"] == pytest.approx(2 / 3)
    assert 0.0 <= float(result["ci95_lower"]) < float(result["ci95_upper"]) <= 1.0


def test_paired_contrast_uses_right_minus_left_and_discordance() -> None:
    observations = [
        _observation("f1", "low", triggered=False),
        _observation("f1", "high", triggered=True),
        _observation("f2", "low", triggered=True),
        _observation("f2", "high", triggered=True),
    ]

    result = paired_contrast(
        observations,
        contrast_id="risk-trigger",
        outcome="triggered",
        level_field="risk",
        left_level="low",
        right_level="high",
        pair_key_fields=("paired_scene_id",),
        seed=7,
    )

    assert result["matched_pair_count"] == 2
    assert result["family_cluster_count"] == 2
    assert result["estimate"] == pytest.approx(0.5)
    assert result["pair_weighted_estimate"] == pytest.approx(0.5)
    assert result["binary_discordant_right_positive"] == 1
    assert result["binary_discordant_left_positive"] == 0
    assert result["binary_exact_p_two_sided"] == 1.0


def test_paired_contrast_reports_missing_parse_dependent_pair() -> None:
    observations = [
        _observation("f1", "low", triggered=False, posterior_confidence=0.4),
        _observation("f1", "high", triggered=False, posterior_confidence=None),
    ]

    result = paired_contrast(
        observations,
        contrast_id="risk-confidence",
        outcome="posterior_confidence",
        level_field="risk",
        left_level="low",
        right_level="high",
        pair_key_fields=("paired_scene_id",),
        seed=7,
    )

    assert result["matched_pair_count"] == 0
    assert result["missing_outcome_pair_count"] == 1
    assert result["estimate"] is None


def test_exact_discordant_and_holm_are_deterministic() -> None:
    assert exact_discordant_p(0, 0) == 1.0
    assert exact_discordant_p(5, 0) == pytest.approx(0.0625)
    assert holm_adjust({"a": 0.01, "b": 0.04, "c": 0.03}) == {
        "a": pytest.approx(0.03),
        "c": pytest.approx(0.06),
        "b": pytest.approx(0.06),
    }
