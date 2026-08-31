"""Deterministic, constraint-aware counterfactual factorial construction."""

from __future__ import annotations

import hashlib
import itertools

from pydantic import BaseModel, ConfigDict, Field

from provtrust.schemas.claim import Claim
from provtrust.schemas.evidence import Evidence, Stance, WarrantLevel
from provtrust.schemas.provenance import EdgeType, ProvenanceEdge, ProvenanceGraph
from provtrust.schemas.source import SourceEntity
from provtrust.schemas.trial import Trial


class SyntheticSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim: Claim
    question: str
    gold_answer: bool | str | float
    candidate_claim: str
    claim_truth: bool | None
    authentic_source: SourceEntity
    alternate_source: SourceEntity
    direct_evidence_text: str
    related_evidence_text: str
    contradiction_text: str


class FactorialDesign(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reliability: tuple[float, ...] = (0.2, 0.8)
    identity_authenticity: tuple[bool, ...] = (False, True)
    attribution_authenticity: tuple[bool, ...] = (False, True)
    warrants: tuple[WarrantLevel, ...] = (
        WarrantLevel.DIRECT_SUPPORT,
        WarrantLevel.RELATED_ONLY,
        WarrantLevel.CONTRADICTION,
    )
    authority_styles: tuple[str, ...] = ("low", "high")
    popularity_levels: tuple[str, ...] = ("low", "high")
    user_endorsements: tuple[bool, ...] = (False, True)
    dependency_conditions: tuple[str, ...] = ("single", "duplicate", "independent")
    document_position: int = Field(default=1, ge=1)
    document_length_tokens: int = Field(default=192, ge=1)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _provenance(family_id: str, dependency: str) -> tuple[ProvenanceGraph, int, int]:
    root = f"{family_id}:root:0"
    nodes: tuple[str, ...]
    edges: tuple[ProvenanceEdge, ...]
    if dependency == "single":
        nodes = (root,)
        edges = ()
        raw_count, effective_count = 1, 1
    elif dependency == "duplicate":
        copies = tuple(f"{family_id}:copy:{index}" for index in range(3))
        nodes = (root, *copies)
        edges = tuple(
            ProvenanceEdge(
                edge_id=f"{family_id}:copied:{index}",
                src_node_id=copy,
                dst_node_id=root,
                edge_type=EdgeType.COPIED_FROM,
                verified=True,
                evidence="synthetic-builder:declared-copy",
            )
            for index, copy in enumerate(copies)
        )
        raw_count, effective_count = 4, 1
    elif dependency == "independent":
        nodes = tuple(f"{family_id}:root:{index}" for index in range(4))
        edges = ()
        raw_count, effective_count = 4, 4
    else:
        raise ValueError(f"unknown dependency condition: {dependency}")
    return ProvenanceGraph(graph_id=f"{family_id}:{dependency}", node_ids=nodes, edges=edges), raw_count, effective_count


def _evidence_text(seed: SyntheticSeed, warrant: WarrantLevel) -> tuple[str, Stance]:
    if warrant is WarrantLevel.DIRECT_SUPPORT:
        return seed.direct_evidence_text, Stance.SUPPORTS
    if warrant is WarrantLevel.CONTRADICTION:
        return seed.contradiction_text, Stance.CONTRADICTS
    return seed.related_evidence_text, Stance.NEUTRAL


def build_factorial(seed: SyntheticSeed, design: FactorialDesign, *, seed_value: int) -> tuple[Trial, ...]:
    trials: list[Trial] = []
    factors = itertools.product(
        design.reliability,
        design.identity_authenticity,
        design.attribution_authenticity,
        design.warrants,
        design.authority_styles,
        design.popularity_levels,
        design.user_endorsements,
        design.dependency_conditions,
    )
    for index, (reliability, identity, attribution, warrant, style, popularity, endorsement, dependency) in enumerate(factors):
        if attribution and not identity:
            continue
        actual = seed.authentic_source if identity else seed.alternate_source
        displayed = seed.authentic_source
        if attribution:
            actual = displayed
        graph, raw_count, effective_count = _provenance(seed.claim.family_id, dependency)
        text, stance = _evidence_text(seed, warrant)
        evidence = Evidence(
            evidence_id=f"{seed.claim.claim_id}:e:{index}",
            document_id=f"{seed.claim.claim_id}:d:{index}",
            claim_id=seed.claim.claim_id,
            source_id=actual.source_id,
            evidence_text=text,
            warrant_level=warrant,
            stance=stance,
            identity_authentic=identity,
            attribution_authentic=attribution,
            snapshot_hash=_digest(text),
        )
        item_key = f"{seed.claim.family_id}|{seed_value}|{index}|{reliability}|{identity}|{attribution}|{warrant}|{style}|{popularity}|{endorsement}|{dependency}"
        item_id = hashlib.sha256(item_key.encode("utf-8")).hexdigest()[:24]
        trials.append(
            Trial(
                item_id=item_id,
                claim=seed.claim,
                question=seed.question,
                gold_answer=seed.gold_answer,
                candidate_claim=seed.candidate_claim,
                claim_truth=seed.claim_truth,
                actual_source=actual,
                displayed_source=displayed,
                source_role=displayed.source_role,
                claim_conditioned_reliability=reliability,
                identity_authentic=identity,
                attribution_authentic=attribution,
                warrant_level=warrant,
                authority_style=style,
                popularity_level=popularity,
                user_endorsement=endorsement,
                document_position=design.document_position,
                document_length_tokens=design.document_length_tokens,
                raw_source_count=raw_count,
                provenance=graph,
                effective_root_count=effective_count,
                evidence=(evidence,),
                verification_required=seed.claim.risk_level in {"high", "critical"},
                intervention="full_factorial",
                seed=seed_value,
            )
        )
    return tuple(trials)
