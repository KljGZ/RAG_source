"""Document-position intervention."""

from __future__ import annotations

from provtrust.interventions.common import update_trial
from provtrust.schemas.trial import Trial


def set_document_position(trial: Trial, position: int) -> Trial:
    if position < 1:
        raise ValueError("document position is one-indexed")
    return update_trial(trial, "order_swap", document_position=position)
