"""Trace a document to verified and unverified provenance roots."""

from __future__ import annotations

import json
from collections import deque

from inspect_ai.tool import Tool, tool

from provtrust.schemas.provenance import ProvenanceGraph


def trace_to_roots(graph: ProvenanceGraph, start_node: str) -> tuple[tuple[str, ...], ...]:
    if start_node not in graph.node_ids:
        raise KeyError(f"unknown provenance node: {start_node}")
    outgoing: dict[str, list[str]] = {node: [] for node in graph.node_ids}
    for edge in graph.edges:
        outgoing[edge.src_node_id].append(edge.dst_node_id)
    traces: list[tuple[str, ...]] = []
    queue: deque[tuple[str, tuple[str, ...]]] = deque([(start_node, (start_node,))])
    while queue:
        node, path = queue.popleft()
        if not outgoing[node]:
            traces.append(path)
        for target in sorted(outgoing[node]):
            queue.append((target, (*path, target)))
    return tuple(traces)


@tool(parallel=True)
def provenance_trace(graph_json: str) -> Tool:
    graph = ProvenanceGraph.model_validate_json(graph_json)

    async def execute(start_node: str) -> str:
        """Trace one controlled document through dependency edges to roots.

        Args:
            start_node: Provenance node from which to begin tracing.

        Returns:
            JSON arrays representing all paths to provenance roots.
        """

        return json.dumps(trace_to_roots(graph, start_node), ensure_ascii=False)

    return execute
