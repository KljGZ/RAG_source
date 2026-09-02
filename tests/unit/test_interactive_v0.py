from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml

from provtrust.datasets.interactive_v0 import (
    InteractivePolicy,
    InteractiveScenario,
    build_interactive_assets,
)
from provtrust.datasets.v0_corpus import V0CorpusSpec
from provtrust.schemas.trial import ToolCondition


def _spec() -> V0CorpusSpec:
    value = yaml.safe_load(
        Path("configs/datasets/v0_paired_v1.yaml").read_text(encoding="utf-8")
    )
    return V0CorpusSpec.model_validate(value)


def test_interactive_design_is_exactly_balanced_and_paired() -> None:
    assets = build_interactive_assets(_spec(), InteractivePolicy.TOOLS_UNPROMPTED)
    assert len(assets.trials) == 160
    assert len({trial.family_id for trial in assets.trials}) == 16
    assert Counter(trial.candidate_answer for trial in assets.trials) == {
        False: 80,
        True: 80,
    }
    assert {trial.metadata["scenario_id"] for trial in assets.trials} == {
        scenario.value for scenario in InteractiveScenario
    }

    pairs: dict[str, list[object]] = {}
    for trial in assets.trials:
        pairs.setdefault(str(trial.metadata["paired_scene_id"]), []).append(trial)
    assert len(pairs) == 80
    assert all(len(pair) == 2 for pair in pairs.values())
    assert all(
        {trial.claim.risk_level.value for trial in pair} == {"low", "high"}
        for pair in pairs.values()
    )


def test_policy_changes_availability_but_not_shared_tool_assets() -> None:
    spec = _spec()
    no_tools = build_interactive_assets(spec, InteractivePolicy.NO_TOOLS)
    unprompted = build_interactive_assets(spec, InteractivePolicy.TOOLS_UNPROMPTED)
    prompted = build_interactive_assets(spec, InteractivePolicy.TOOLS_PROMPTED)
    assert no_tools.documents == unprompted.documents == prompted.documents
    assert no_tools.snapshots == unprompted.snapshots == prompted.snapshots
    assert all(
        trial.tool_condition is ToolCondition.UNAVAILABLE for trial in no_tools.trials
    )
    assert {
        trial.tool_condition for trial in unprompted.trials
    } == {ToolCondition.AVAILABLE_NOT_REQUIRED, ToolCondition.AVAILABLE_REQUIRED}
    assert all(
        trial.tool_condition is ToolCondition.AVAILABLE_REQUIRED
        for trial in prompted.trials
    )
