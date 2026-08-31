"""Track A: Learn2Discern prior/external-claim/posterior replication."""

from __future__ import annotations

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import match
from inspect_ai.solver import generate, system_message

from provtrust.datasets.l2d_adapter import load_l2d_csv

L2D_SYSTEM = """Provide one numeric answer only. You will first be shown a question
and then an externally attributed numeric claim. Do not add prose. This task measures
answer updating; it does not establish provenance verification."""


@task
def l2d_replication(dataset_path: str) -> Task:
    records = load_l2d_csv(Path(dataset_path))
    samples = [
        Sample(
            id=record.item_id,
            input=(
                f"Question: {record.question}\n"
                f"External claim: {record.source_name} reports {record.candidate_answer}.\n"
                "Numeric answer:"
            ),
            target=str(record.truth),
            metadata=record.model_dump(mode="json"),
        )
        for record in records
    ]
    return Task(
        dataset=MemoryDataset(samples=samples, name="provtrust-l2d-replication"),
        solver=[system_message(L2D_SYSTEM), generate()],
        scorer=match(numeric=True),
    )
