"""Track B: static source causal decomposition."""

from inspect_ai import Task, task

from provtrust.tasks.common import build_trial_task


@task
def static_factorial(dataset_path: str) -> Task:
    return build_trial_task(dataset_path, track="static_factorial")
