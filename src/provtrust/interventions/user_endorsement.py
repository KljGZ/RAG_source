"""User-endorsement proxy-cue intervention."""

from __future__ import annotations

from provtrust.interventions.common import update_trial
from provtrust.schemas.trial import Trial


def set_user_endorsement(trial: Trial, endorsed: bool) -> Trial:
    return update_trial(trial, "user_endorsement", user_endorsement=endorsed)
