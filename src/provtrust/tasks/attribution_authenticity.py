"""Track C1: source identity and attribution authenticity."""

from inspect_ai import Task, task

from provtrust.tasks.common import build_trial_task


@task
def attribution_authenticity(dataset_path: str) -> Task:
    return build_trial_task(dataset_path, track="attribution_authenticity")
