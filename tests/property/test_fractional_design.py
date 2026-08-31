from __future__ import annotations

from provtrust.datasets.synthetic_builder import FactorialDesign, SyntheticSeed, build_factorial
from provtrust.schemas.source import SourceEntity
from provtrust.schemas.trial import Trial


def test_v0_fractional_design_is_deterministic_and_bounded(smoke_trial: Trial) -> None:
    alternate = SourceEntity.model_validate(
        {
            **smoke_trial.actual_source.model_dump(mode="python"),
            "source_id": "controlled-alternate",
            "canonical_name": "Controlled Alternate Publisher",
            "displayed_name": "Controlled Alternate Publisher",
            "actual_publisher": "Controlled Alternate Publisher",
        }
    )
    seed = SyntheticSeed(
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
    design = FactorialDesign(variants_per_family=16)
    left = build_factorial(seed, design, seed_value=17)
    right = build_factorial(seed, design, seed_value=17)
    assert left == right
    assert len(left) == 16
    assert len({trial.item_id for trial in left}) == 16
    assert {trial.identity_authentic for trial in left} == {False, True}
    assert {trial.attribution_authentic for trial in left} == {False, True}
    assert {trial.authority_style for trial in left} == {"low", "high"}
    assert {trial.effective_root_count for trial in left} >= {1, 4}
