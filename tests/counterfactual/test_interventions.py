from __future__ import annotations

from provtrust.interventions.authority_style import set_authority_style
from provtrust.interventions.duplicate_source import duplicate_source
from provtrust.interventions.source_dependency import set_independent_roots
from provtrust.interventions.user_endorsement import set_user_endorsement
from provtrust.schemas.trial import Trial


def test_proxy_intervention_preserves_scientific_content(smoke_trial: Trial) -> None:
    changed = set_authority_style(smoke_trial, "high")
    assert changed.family_id == smoke_trial.family_id
    assert changed.claim == smoke_trial.claim
    assert changed.evidence == smoke_trial.evidence
    assert changed.authority_style == "high"
    assert changed.item_id != smoke_trial.item_id


def test_duplicate_and_independent_sources_are_distinct(smoke_trial: Trial) -> None:
    duplicated = duplicate_source(smoke_trial, copies=4)
    independent = set_independent_roots(smoke_trial, roots=4)
    assert duplicated.raw_source_count == independent.raw_source_count == 4
    assert duplicated.effective_root_count == 1
    assert independent.effective_root_count == 4


def test_interventions_are_deterministic(smoke_trial: Trial) -> None:
    left = set_user_endorsement(smoke_trial, True)
    right = set_user_endorsement(smoke_trial, True)
    assert left == right
