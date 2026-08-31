"""False attribution intervention distinct from site-identity authenticity."""

from __future__ import annotations

from provtrust.interventions.common import update_trial
from provtrust.schemas.source import SourceEntity
from provtrust.schemas.trial import Trial


def spoof_attribution(trial: Trial, claimed_source: SourceEntity) -> Trial:
    evidence = tuple(item.model_copy(update={"attribution_authentic": False}) for item in trial.evidence)
    return update_trial(
        trial,
        "attribution_spoof",
        displayed_source=claimed_source,
        source_role=claimed_source.source_role,
        attribution_authentic=False,
        evidence=evidence,
    )
