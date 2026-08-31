"""Create dependent copies that share one verified provenance root."""

from __future__ import annotations

from provtrust.interventions.common import update_trial
from provtrust.schemas.provenance import EdgeType, ProvenanceEdge, ProvenanceGraph
from provtrust.schemas.trial import Trial


def duplicate_source(trial: Trial, *, copies: int) -> Trial:
    if copies < 2:
        raise ValueError("duplicate condition requires at least two displayed sources")
    root = trial.provenance.roots()[0]
    copy_nodes = tuple(f"{trial.item_id}:duplicate:{index}" for index in range(copies - 1))
    graph = ProvenanceGraph(
        graph_id=f"{trial.provenance.graph_id}:duplicates:{copies}",
        node_ids=(root, *copy_nodes),
        edges=tuple(
            ProvenanceEdge(
                edge_id=f"{trial.item_id}:duplicate-edge:{index}",
                src_node_id=node,
                dst_node_id=root,
                edge_type=EdgeType.COPIED_FROM,
                verified=True,
                evidence="intervention:declared-copy",
            )
            for index, node in enumerate(copy_nodes)
        ),
    )
    return update_trial(
        trial,
        "duplicate_source",
        provenance=graph,
        raw_source_count=copies,
        effective_root_count=1,
    )
