"""Document-length control intervention."""

from __future__ import annotations

from provtrust.interventions.common import update_trial
from provtrust.schemas.trial import Trial


def set_document_length(trial: Trial, tokens: int) -> Trial:
    if tokens < 1:
        raise ValueError("document length must be positive")
    return update_trial(trial, "length_control", document_length_tokens=tokens)
