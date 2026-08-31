"""Displayed source-label swap with content held fixed."""

from __future__ import annotations

from provtrust.interventions.common import update_trial
from provtrust.schemas.source import SourceEntity
from provtrust.schemas.trial import Trial


def swap_displayed_source(trial: Trial, displayed_source: SourceEntity) -> Trial:
    evidence = tuple(item.model_copy(update={"attribution_authentic": False}) for item in trial.evidence)
    return update_trial(
        trial,
        "source_swap",
        displayed_source=displayed_source,
        source_role=displayed_source.source_role,
        attribution_authentic=False,
        evidence=evidence,
    )
