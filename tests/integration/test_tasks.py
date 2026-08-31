from __future__ import annotations

from provtrust.tasks.static_factorial import static_factorial


def test_static_inspect_task_builds_without_model_call() -> None:
    task = static_factorial(dataset_path="benchmark/synthetic/smoke.jsonl")
    assert len(task.dataset) == 1
