"""Track E: tool-mediated provenance verification."""

from inspect_ai import Task, task

from provtrust.tasks.common import build_trial_task
from provtrust.tools.canonical_lookup import canonical_lookup
from provtrust.tools.controlled_search import controlled_search
from provtrust.tools.find_evidence import find_evidence
from provtrust.tools.open_snapshot import open_snapshot
from provtrust.tools.verify_identifier import verify_identifier


@task
def interactive_verification(
    dataset_path: str,
    search_index_path: str,
    snapshot_root: str,
    source_registry_path: str,
    identifier_registry_path: str,
) -> Task:
    tools = (
        controlled_search(search_index_path),
        open_snapshot(snapshot_root),
        canonical_lookup(source_registry_path),
        find_evidence(),
        verify_identifier(identifier_registry_path),
    )
    return build_trial_task(
        dataset_path, track="interactive_verification", tools=tools, message_limit=12
    )
