"""Authority-style manipulation without changing evidence support."""

from __future__ import annotations

from provtrust.interventions.common import update_trial
from provtrust.schemas.trial import Trial


def set_authority_style(trial: Trial, style: str, *, precision_detail: str | None = None) -> Trial:
    if not style.strip():
        raise ValueError("authority style must not be empty")
    changes: dict[str, str] = {"authority_style": style}
    if precision_detail is not None:
        changes["precision_detail"] = precision_detail
    return update_trial(trial, "authority_style", **changes)
