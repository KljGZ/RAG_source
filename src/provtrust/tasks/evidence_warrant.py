"""Track C2: evidence warrant/permission."""

from inspect_ai import Task, task

from provtrust.tasks.common import build_trial_task


@task
def evidence_warrant(dataset_path: str) -> Task:
    return build_trial_task(dataset_path, track="evidence_warrant")
