"""Manipulate source independence while holding displayed count fixed."""

from __future__ import annotations

from provtrust.interventions.common import update_trial
from provtrust.schemas.provenance import ProvenanceGraph
from provtrust.schemas.trial import Trial


def set_independent_roots(trial: Trial, *, roots: int) -> Trial:
    if roots < 1:
        raise ValueError("at least one provenance root is required")
    nodes = tuple(f"{trial.item_id}:independent-root:{index}" for index in range(roots))
    graph = ProvenanceGraph(
        graph_id=f"{trial.provenance.graph_id}:independent:{roots}", node_ids=nodes
    )
    return update_trial(
        trial,
        "source_independence",
        provenance=graph,
        raw_source_count=roots,
        effective_root_count=roots,
    )
