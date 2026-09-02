"""Trace a document to verified and unverified provenance roots."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

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


class ProvenanceRegistry:
    """Frozen document-level provenance and temporal relations."""

    def __init__(self, records: dict[str, dict[str, Any]], environment_version: str) -> None:
        self.records = records
        self.environment_version = environment_version

    @classmethod
    def from_json(cls, path: Path) -> ProvenanceRegistry:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise TypeError("provenance registry must contain an object")
        records = value.get("documents")
        version = value.get("environment_version")
        if not isinstance(records, dict) or not all(
            isinstance(key, str) and isinstance(record, dict)
            for key, record in records.items()
        ):
            raise TypeError("provenance registry documents must be an object mapping")
        if not isinstance(version, str) or not version:
            raise TypeError("provenance registry requires environment_version")
        return cls(records, version)

    def trace(self, document_id: str) -> dict[str, Any]:
        record = self.records.get(document_id)
        if record is None:
            return {
                "status": "not_found",
                "document_id": document_id,
                "environment_version": self.environment_version,
                "record": None,
            }
        return {
            "status": "found",
            "document_id": document_id,
            "environment_version": self.environment_version,
            "record": record,
        }


@tool(parallel=True)
def provenance_trace(registry_path: str) -> Tool:
    registry = ProvenanceRegistry.from_json(Path(registry_path))

    async def execute(document_id: str) -> str:
        """Trace one controlled document through source and temporal relations.

        Args:
            document_id: Exact controlled document identifier to trace.

        Returns:
            JSON record with source roots, timestamps, and verified/unverified edges.
        """

        return json.dumps(registry.trace(document_id), ensure_ascii=False)

    return execute
