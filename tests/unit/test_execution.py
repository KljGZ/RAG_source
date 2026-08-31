from __future__ import annotations

import pytest

from provtrust.execution.checkpoint import CheckpointStore, ItemState
from provtrust.execution.cost_ledger import BudgetExceeded, CostLedger
from provtrust.execution.sharding import shard_for_item


def test_checkpoint_state_machine(tmp_path) -> None:
    store = CheckpointStore(tmp_path / "checkpoint.sqlite")
    store.initialize(("a",))
    store.transition("a", ItemState.RUNNING)
    store.transition("a", ItemState.SUCCEEDED, output_path="result.json")
    assert store.state("a") is ItemState.SUCCEEDED
    with pytest.raises(ValueError, match="illegal"):
        store.transition("a", ItemState.RUNNING)


def test_cost_ledger_hard_gate(tmp_path) -> None:
    ledger = CostLedger(tmp_path / "cost.sqlite", budget_usd=1.0)
    ledger.reserve_and_record(
        run_id="r", item_id="i", provider="p", model="m",
        input_tokens=1, output_tokens=1, cost_usd=0.75,
    )
    with pytest.raises(BudgetExceeded):
        ledger.reserve_and_record(
            run_id="r", item_id="j", provider="p", model="m",
            input_tokens=1, output_tokens=1, cost_usd=0.30,
        )


def test_sharding_is_stable() -> None:
    assert shard_for_item("item", 7, seed=3) == shard_for_item("item", 7, seed=3)
