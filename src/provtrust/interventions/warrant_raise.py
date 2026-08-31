"""Evidence-warrant intervention with an explicit ordinal scale."""

from __future__ import annotations

import hashlib

from provtrust.interventions.common import update_trial
from provtrust.schemas.evidence import Stance, WarrantLevel
from provtrust.schemas.trial import Trial

WARRANT_SCORE = {
    WarrantLevel.CONTRADICTION: -1.0,
    WarrantLevel.UNSUPPORTED: 0.0,
    WarrantLevel.RELATED_ONLY: 0.25,
    WarrantLevel.PARTIAL_SUPPORT: 0.6,
    WarrantLevel.DIRECT_SUPPORT: 1.0,
}


def set_warrant(trial: Trial, warrant: WarrantLevel, *, evidence_text: str) -> Trial:
    if not evidence_text.strip():
        raise ValueError("evidence text must not be empty")
    if warrant is WarrantLevel.CONTRADICTION:
        stance = Stance.CONTRADICTS
    elif warrant in {WarrantLevel.DIRECT_SUPPORT, WarrantLevel.PARTIAL_SUPPORT}:
        stance = Stance.SUPPORTS
    else:
        stance = Stance.NEUTRAL
    evidence = tuple(
        item.model_copy(
            update={
                "evidence_text": evidence_text,
                "snapshot_hash": hashlib.sha256(evidence_text.encode("utf-8")).hexdigest(),
                "warrant_level": warrant,
                "stance": stance,
            }
        )
        for item in trial.evidence
    )
    return update_trial(trial, "warrant", warrant_level=warrant, evidence=evidence)
