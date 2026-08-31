from __future__ import annotations

import json
from pathlib import Path

import pytest

from provtrust.schemas.trial import Trial


@pytest.fixture()
def smoke_trial() -> Trial:
    path = Path("benchmark/synthetic/smoke.jsonl")
    return Trial.model_validate(json.loads(path.read_text(encoding="utf-8").strip()))
