"""Track D: dependent duplication and consensus laundering."""

from inspect_ai import Task, task

from provtrust.tasks.common import build_trial_task


@task
def consensus_laundering(dataset_path: str) -> Task:
    return build_trial_task(dataset_path, track="consensus_laundering")
