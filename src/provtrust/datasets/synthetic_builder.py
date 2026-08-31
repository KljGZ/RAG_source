"""Deterministic, constraint-aware counterfactual factorial construction."""

from __future__ import annotations

import hashlib
import itertools
from typing import Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, Field

from provtrust.schemas.claim import Claim
from provtrust.schemas.evidence import Evidence, Stance, WarrantLevel
from provtrust.schemas.provenance import EdgeType, ProvenanceEdge, ProvenanceGraph
from provtrust.schemas.source import SourceEntity
from provtrust.schemas.trial import ToolCondition, Trial


class SyntheticSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim: Claim
    question: str
    gold_answer: bool | str | float
    candidate_claim: str
    candidate_answer: bool | str | float
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
    familiarity_levels: tuple[str, ...] = ("low", "high")
    precision_details: tuple[str, ...] = ("low", "high")
    user_endorsements: tuple[bool, ...] = (False, True)
    dependency_conditions: tuple[str, ...] = ("single", "duplicate", "independent")
    document_positions: tuple[int, ...] = (1, 3)
    document_length_tokens: tuple[int, ...] = (96, 192)
    design: Literal["fractional", "full"] = "fractional"
    variants_per_family: int = Field(default=16, ge=2)


class _FactorCell(NamedTuple):
    reliability: float
    identity: bool
    attribution: bool
    warrant: WarrantLevel
    style: str
    popularity: str
    familiarity: str
    precision: str
    endorsement: bool
    dependency: str
    position: int
    length: int


def _cell_levels(cell: _FactorCell) -> tuple[str, ...]:
    return tuple(str(value) for value in cell)


def _candidate_cells(design: FactorialDesign) -> tuple[_FactorCell, ...]:
    cells: list[_FactorCell] = []
    factors = itertools.product(
        design.reliability,
        design.identity_authenticity,
        design.attribution_authenticity,
        design.warrants,
        design.authority_styles,
        design.popularity_levels,
        design.familiarity_levels,
        design.precision_details,
        design.user_endorsements,
        design.dependency_conditions,
        design.document_positions,
        design.document_length_tokens,
    )
    for values in factors:
        cell = _FactorCell(*values)
        if cell.attribution and not cell.identity:
            continue
        cells.append(cell)
    return tuple(cells)


def _fractional_cells(
    candidates: tuple[_FactorCell, ...], *, count: int, seed_value: int
) -> tuple[_FactorCell, ...]:
    """Select a deterministic, level-balanced, maximin fractional design."""

    if count > len(candidates):
        raise ValueError("variants_per_family exceeds the valid factorial cells")
    selected: list[_FactorCell] = []
    level_counts: dict[tuple[int, str], int] = {}
    remaining = set(candidates)
    while len(selected) < count:
        best: _FactorCell | None = None
        best_score: tuple[int, float, int] | None = None
        for candidate in remaining:
            levels = _cell_levels(candidate)
            distance = (
                min(
                    sum(left != right for left, right in zip(levels, _cell_levels(other)))
                    for other in selected
                )
                if selected
                else len(levels)
            )
            balance = sum(
                1.0 / (1.0 + level_counts.get((index, level), 0))
                for index, level in enumerate(levels)
            )
            tie = int.from_bytes(
                hashlib.sha256(f"{seed_value}|{candidate}".encode()).digest()[:8], "big"
            )
            score = (distance, balance, -tie)
            if best_score is None or score > best_score:
                best = candidate
                best_score = score
        if best is None:
            raise AssertionError("fractional design selection exhausted unexpectedly")
        selected.append(best)
        remaining.remove(best)
        for index, level in enumerate(_cell_levels(best)):
            level_counts[(index, level)] = level_counts.get((index, level), 0) + 1
    return tuple(selected)


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
    return (
        ProvenanceGraph(graph_id=f"{family_id}:{dependency}", node_ids=nodes, edges=edges),
        raw_count,
        effective_count,
    )


def _evidence_text(seed: SyntheticSeed, warrant: WarrantLevel) -> tuple[str, Stance]:
    if warrant is WarrantLevel.DIRECT_SUPPORT:
        return seed.direct_evidence_text, Stance.SUPPORTS
    if warrant is WarrantLevel.CONTRADICTION:
        return seed.contradiction_text, Stance.CONTRADICTS
    return seed.related_evidence_text, Stance.NEUTRAL


def build_factorial(
    seed: SyntheticSeed, design: FactorialDesign, *, seed_value: int
) -> tuple[Trial, ...]:
    trials: list[Trial] = []
    candidates = _candidate_cells(design)
    factors = (
        candidates
        if design.design == "full"
        else _fractional_cells(candidates, count=design.variants_per_family, seed_value=seed_value)
    )
    for index, cell in enumerate(factors):
        reliability = cell.reliability
        identity = cell.identity
        attribution = cell.attribution
        warrant = cell.warrant
        style = cell.style
        popularity = cell.popularity
        endorsement = cell.endorsement
        dependency = cell.dependency
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
        item_key = f"{seed.claim.family_id}|{seed_value}|{index}|{cell}"
        item_id = hashlib.sha256(item_key.encode("utf-8")).hexdigest()[:24]
        trials.append(
            Trial(
                item_id=item_id,
                claim=seed.claim,
                question=seed.question,
                gold_answer=seed.gold_answer,
                candidate_claim=seed.candidate_claim,
                candidate_answer=seed.candidate_answer,
                claim_truth=seed.claim_truth,
                actual_source=actual,
                displayed_source=displayed,
                source_role=displayed.source_role,
                claim_conditioned_reliability=reliability,
                identity_authentic=identity,
                attribution_authentic=attribution,
                warrant_level=warrant,
                authority_style=style,
                precision_detail=cell.precision,
                popularity_level=popularity,
                familiarity_level=cell.familiarity,
                user_endorsement=endorsement,
                document_position=cell.position,
                document_length_tokens=cell.length,
                raw_source_count=raw_count,
                provenance=graph,
                effective_root_count=effective_count,
                evidence=(evidence,),
                tool_condition=(
                    ToolCondition.AVAILABLE_REQUIRED
                    if seed.claim.risk_level in {"high", "critical"}
                    else ToolCondition.AVAILABLE_NOT_REQUIRED
                ),
                verification_required=seed.claim.risk_level in {"high", "critical"},
                intervention=f"{design.design}_factorial",
                intervention_vector={
                    "claim_conditioned_reliability": reliability,
                    "identity_authenticity": identity,
                    "attribution_authenticity": attribution,
                    "evidence_warrant": warrant.value,
                    "authority_style": style,
                    "popularity": popularity,
                    "familiarity": cell.familiarity,
                    "precision_detail": cell.precision,
                    "user_endorsement": endorsement,
                    "source_dependency": dependency,
                    "document_position": cell.position,
                    "document_length": cell.length,
                },
                seed=seed_value,
            )
        )
    return tuple(trials)
