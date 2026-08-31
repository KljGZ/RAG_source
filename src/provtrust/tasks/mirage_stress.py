"""Isolated MIRAGE stress task adapter."""

from pathlib import Path

from inspect_ai import Task, task

from provtrust.datasets.mirage_adapter import load_mirage_manifest
from provtrust.tasks.common import build_trial_task


@task
def mirage_stress(dataset_path: str, safety_manifest_path: str) -> Task:
    load_mirage_manifest(Path(safety_manifest_path))
    return build_trial_task(dataset_path, track="mirage_stress")
