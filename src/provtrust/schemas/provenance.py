"""Provenance graph data contracts."""

from __future__ import annotations

from enum import StrEnum

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EdgeType(StrEnum):
    PUBLISHED_BY = "published_by"
    CITES = "cites"
    COPIED_FROM = "copied_from"
    DERIVED_FROM = "derived_from"
    PARAPHRASED_FROM = "paraphrased_from"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UPDATES = "updates"


class ProvenanceEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    edge_id: str = Field(min_length=1)
    src_node_id: str = Field(min_length=1)
    dst_node_id: str = Field(min_length=1)
    edge_type: EdgeType
    verified: bool
    evidence: str | None = None

    @model_validator(mode="after")
    def reject_self_loop(self) -> ProvenanceEdge:
        if self.src_node_id == self.dst_node_id:
            raise ValueError("provenance self-loops are not allowed")
        if self.verified and not self.evidence:
            raise ValueError("verified edges require an audit evidence reference")
        return self


class ProvenanceGraph(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    graph_id: str = Field(min_length=1)
    node_ids: tuple[str, ...]
    edges: tuple[ProvenanceEdge, ...] = ()

    @model_validator(mode="after")
    def validate_graph(self) -> ProvenanceGraph:
        nodes = set(self.node_ids)
        if len(nodes) != len(self.node_ids):
            raise ValueError("provenance node identifiers must be unique")
        edge_ids = [edge.edge_id for edge in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("provenance edge identifiers must be unique")
        for edge in self.edges:
            if edge.src_node_id not in nodes or edge.dst_node_id not in nodes:
                raise ValueError("provenance edge references an unknown node")
        graph = nx.DiGraph()
        graph.add_nodes_from(nodes)
        graph.add_edges_from((edge.src_node_id, edge.dst_node_id) for edge in self.edges)
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("provenance dependency graph must be acyclic")
        return self

    def roots(self) -> tuple[str, ...]:
        graph = nx.DiGraph()
        graph.add_nodes_from(self.node_ids)
        graph.add_edges_from((edge.src_node_id, edge.dst_node_id) for edge in self.edges)
        return tuple(sorted(node for node, degree in graph.out_degree() if degree == 0))
