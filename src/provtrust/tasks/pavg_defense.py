"""Track G: PAVG-assisted answer and abstention task."""

from inspect_ai import Task, task

from provtrust.tasks.common import build_trial_task


@task
def pavg_defense(dataset_path: str) -> Task:
    return build_trial_task(dataset_path, track="pavg_defense")
