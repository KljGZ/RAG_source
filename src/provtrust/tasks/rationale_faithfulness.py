"""Track F: declared factor weights versus counterfactual causal effects."""

from inspect_ai import Task, task

from provtrust.tasks.common import build_trial_task


@task
def rationale_faithfulness(dataset_path: str) -> Task:
    return build_trial_task(dataset_path, track="rationale_faithfulness")
