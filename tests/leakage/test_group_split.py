from __future__ import annotations

from provtrust.datasets.split import assign_grouped_splits
from provtrust.datasets.validate import validate_trials
from provtrust.interventions.authority_style import set_authority_style
from provtrust.interventions.user_endorsement import set_user_endorsement
from provtrust.schemas.trial import Trial


def test_family_variants_never_cross_split(smoke_trial: Trial) -> None:
    trials = (
        smoke_trial,
        set_authority_style(smoke_trial, "high"),
        set_user_endorsement(smoke_trial, True),
    )
    assignments = assign_grouped_splits(trials, seed=7)
    assert len({entry.split for entry in assignments}) == 1
    assert validate_trials(trials, assignments).valid


def test_split_is_order_independent(smoke_trial: Trial) -> None:
    variant = set_authority_style(smoke_trial, "high")
    forward = assign_grouped_splits((smoke_trial, variant), seed=19)
    reverse = assign_grouped_splits((variant, smoke_trial), seed=19)
    assert {(row.item_id, row.split) for row in forward} == {
        (row.item_id, row.split) for row in reverse
    }
