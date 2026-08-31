from __future__ import annotations

import json

from provtrust.datasets.stimulus_audit import audit_paired_stimuli
from provtrust.datasets.synthetic_builder import FactorialDesign, SyntheticSeed, build_factorial
from provtrust.schemas.source import SourceEntity
from provtrust.schemas.trial import Trial
from provtrust.tasks.common import render_prior, render_trial


def _seed(smoke_trial: Trial) -> SyntheticSeed:
    alternate = SourceEntity.model_validate(
        {
            **smoke_trial.actual_source.model_dump(mode="python"),
            "source_id": "controlled-alternate",
            "canonical_name": "Controlled Alternate Publisher",
            "displayed_name": "Controlled Alternate Publisher",
            "actual_publisher": "Controlled Alternate Publisher",
        }
    )
    return SyntheticSeed(
        claim=smoke_trial.claim,
        question=smoke_trial.question,
        gold_answer=smoke_trial.gold_answer,
        candidate_claim=smoke_trial.candidate_claim,
        candidate_answer=smoke_trial.candidate_answer,
        claim_truth=smoke_trial.claim_truth,
        authentic_source=smoke_trial.actual_source,
        alternate_source=alternate,
        direct_evidence_text="The controlled record directly supports the candidate.",
        related_evidence_text="The controlled record discusses the same topic only.",
        contradiction_text="The controlled record contradicts the candidate.",
    )


def test_v0_paired_design_is_deterministic_and_exactly_matched(smoke_trial: Trial) -> None:
    seed = _seed(smoke_trial)
    design = FactorialDesign()
    left = build_factorial(seed, design, seed_value=17)
    right = build_factorial(seed, design, seed_value=17)
    assert left == right
    assert len(left) == 15
    assert len({trial.item_id for trial in left}) == 15
    assert {trial.identity_authentic for trial in left} == {False, True}
    assert {trial.attribution_authentic for trial in left} == {False, True}
    assert {trial.authority_style for trial in left} == {"low", "high"}
    assert {trial.effective_root_count for trial in left} >= {1, 4}

    by_cell = {str(trial.metadata["design_cell_id"]): trial for trial in left}
    for trial in left:
        control_cell = trial.metadata["control_cell_id"]
        factor = trial.metadata["contrast_factor"]
        if control_cell is None:
            assert factor is None
            continue
        control = by_cell[str(control_cell)]
        changed = {
            name
            for name, value in trial.intervention_vector.items()
            if control.intervention_vector[name] != value
        }
        assert changed == {factor}


def test_v0_paired_contrasts_are_model_visible_without_gold_leakage(
    smoke_trial: Trial,
) -> None:
    trials = build_factorial(_seed(smoke_trial), FactorialDesign(), seed_value=17)
    by_cell = {str(trial.metadata["design_cell_id"]): trial for trial in trials}
    priors = {render_prior(trial, track="static_factorial") for trial in trials}
    assert len(priors) == 1

    for trial in trials:
        rendered = render_trial(trial, track="static_factorial")
        payload = json.loads(rendered)
        assert "gold_answer" not in rendered
        assert "claim_truth" not in rendered
        assert "actual_source" not in rendered
        assert payload["protocol"] == "audited_static_v1"
        control_cell = trial.metadata["control_cell_id"]
        if control_cell is not None:
            assert rendered != render_trial(by_cell[str(control_cell)], track="static_factorial")

    audit = audit_paired_stimuli(trials)
    assert audit.valid, audit.errors
    assert audit.prior_invariant
    assert not audit.gold_leakage_detected
    assert set(audit.contrast_counts) == {
        "claim_conditioned_reliability",
        "identity_authenticity",
        "attribution_authenticity",
        "evidence_warrant",
        "raw_source_count",
        "source_independence",
        "authority_style",
        "popularity",
        "familiarity",
        "precision_detail",
        "user_endorsement",
        "document_position",
        "document_length",
    }
