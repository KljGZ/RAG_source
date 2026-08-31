"""Build dependency graphs only from declared/audited edges."""

from __future__ import annotations

from provtrust.schemas.provenance import ProvenanceEdge, ProvenanceGraph


def build_provenance_graph(
    graph_id: str, node_ids: tuple[str, ...], edges: tuple[ProvenanceEdge, ...]
) -> ProvenanceGraph:
    return ProvenanceGraph(graph_id=graph_id, node_ids=node_ids, edges=edges)


def verified_subgraph(graph: ProvenanceGraph) -> ProvenanceGraph:
    verified_edges = tuple(edge for edge in graph.edges if edge.verified)
    return ProvenanceGraph(
        graph_id=f"{graph.graph_id}:verified", node_ids=graph.node_ids, edges=verified_edges
    )
