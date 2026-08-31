"""Shared intervention helpers."""

from __future__ import annotations

import hashlib
from typing import Any

from provtrust.schemas.trial import Trial


def derived_item_id(trial: Trial, name: str, parameters: dict[str, Any]) -> str:
    encoded = "|".join(
        [trial.item_id, name, *(f"{key}={parameters[key]}" for key in sorted(parameters))]
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]


def update_trial(trial: Trial, name: str, **changes: Any) -> Trial:
    item_id = derived_item_id(trial, name, changes)
    payload = trial.model_dump(mode="python")
    payload.update({"item_id": item_id, "intervention": name, **changes})
    return Trial.model_validate(payload)
