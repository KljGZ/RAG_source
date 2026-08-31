from __future__ import annotations

from pathlib import Path

from provtrust.tasks.attribution_authenticity import attribution_authenticity
from provtrust.tasks.consensus_laundering import consensus_laundering
from provtrust.tasks.evidence_warrant import evidence_warrant
from provtrust.tasks.interactive_verification import interactive_verification
from provtrust.tasks.l2d_replication import l2d_replication
from provtrust.tasks.mirage_stress import mirage_stress
from provtrust.tasks.pavg_defense import pavg_defense
from provtrust.tasks.rationale_faithfulness import rationale_faithfulness
from provtrust.tasks.static_factorial import static_factorial


def test_static_inspect_task_builds_without_model_call() -> None:
    task = static_factorial(dataset_path="benchmark/synthetic/smoke.jsonl")
    assert len(task.dataset) == 1


def test_every_pgsd_track_builds_without_model_call() -> None:
    dataset = "benchmark/synthetic/smoke.jsonl"
    simple_tasks = (
        attribution_authenticity(dataset),
        evidence_warrant(dataset),
        consensus_laundering(dataset),
        rationale_faithfulness(dataset),
        mirage_stress(dataset, "benchmark/manifests/mirage-smoke.yaml"),
    )
    tool_arguments = {
        "dataset_path": dataset,
        "search_index_path": "web_env/search_index/documents.jsonl",
        "snapshot_root": "web_env/source_snapshots",
        "source_registry_path": "web_env/canonical_sources/registry.json",
        "identifier_registry_path": "web_env/canonical_sources/identifiers.json",
    }
    tool_tasks = (
        interactive_verification(**tool_arguments),
        pavg_defense(**tool_arguments),
    )
    assert all(len(task.dataset) == 1 for task in (*simple_tasks, *tool_tasks))


def test_l2d_two_stage_task_builds_without_model_call(tmp_path: Path) -> None:
    dataset = tmp_path / "l2d.csv"
    dataset.write_text(
        "item_id,question_id,question,truth,prior_answer,candidate_answer,source,reliability,popularity\n"
        "i-1,f-1,What is the controlled value?,10,,12,Controlled Source,0.8,0.4\n",
        encoding="utf-8",
    )
    task = l2d_replication(str(dataset))
    assert len(task.dataset) == 1
