from __future__ import annotations

import pytest
from pydantic import ValidationError

from provtrust.schemas.provenance import EdgeType, ProvenanceEdge, ProvenanceGraph
from provtrust.schemas.trial import Trial


def test_smoke_trial_has_consistent_roots(smoke_trial: Trial) -> None:
    assert smoke_trial.effective_root_count == len(smoke_trial.provenance.roots()) == 1
    assert smoke_trial.family_id == "smoke-family-001"


def test_authentic_attribution_requires_identity(smoke_trial: Trial) -> None:
    payload = smoke_trial.model_dump(mode="python")
    payload["identity_authentic"] = False
    with pytest.raises(ValidationError, match="authentic attribution"):
        Trial.model_validate(payload)


def test_provenance_cycle_is_rejected() -> None:
    with pytest.raises(ValidationError, match="acyclic"):
        ProvenanceGraph(
            graph_id="cycle",
            node_ids=("a", "b"),
            edges=(
                ProvenanceEdge(
                    edge_id="ab",
                    src_node_id="a",
                    dst_node_id="b",
                    edge_type=EdgeType.COPIED_FROM,
                    verified=True,
                    evidence="fixture",
                ),
                ProvenanceEdge(
                    edge_id="ba",
                    src_node_id="b",
                    dst_node_id="a",
                    edge_type=EdgeType.COPIED_FROM,
                    verified=True,
                    evidence="fixture",
                ),
            ),
        )
