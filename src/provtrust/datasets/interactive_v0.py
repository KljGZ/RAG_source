"""Deterministic closed-world assets for interactive-verification V0."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from provtrust.datasets.v0_corpus import V0CorpusSpec, V0FamilySpec
from provtrust.schemas.claim import Claim, RiskLevel
from provtrust.schemas.evidence import Evidence, Stance, WarrantLevel
from provtrust.schemas.provenance import EdgeType, ProvenanceEdge, ProvenanceGraph
from provtrust.schemas.source import SourceEntity, SourceRole, SourceType
from provtrust.schemas.trial import ToolCondition, Trial

ENVIRONMENT_VERSION = "interactive-v0.1"


class InteractivePolicy(StrEnum):
    NO_TOOLS = "no_tools"
    TOOLS_UNPROMPTED = "tools_unprompted"
    TOOLS_PROMPTED = "tools_prompted"
    TOOLS_GATED = "tools_gated"


class InteractiveScenario(StrEnum):
    AUTHENTIC_DIRECT = "c1_authentic_direct"
    AUTHENTIC_PARTIAL = "c2_authentic_partial"
    FALSE_ATTRIBUTION = "c3_false_attribution"
    SPOOFED_IDENTITY = "c4_spoofed_identity"
    MISSING_REFERENCE = "c5_missing_reference"


@dataclass(frozen=True)
class InteractiveAssets:
    trials: tuple[Trial, ...]
    documents: tuple[dict[str, Any], ...]
    snapshots: dict[str, bytes]
    source_registry: tuple[dict[str, Any], ...]
    identifier_registry: dict[str, dict[str, Any]]
    provenance_registry: dict[str, Any]


@dataclass(frozen=True)
class _Sources:
    canonical: SourceEntity
    reporter: SourceEntity
    replica: SourceEntity
    nonexistent: SourceEntity


@dataclass(frozen=True)
class _Scenario:
    scenario: InteractiveScenario
    candidate_matches_gold: bool
    actual_source: SourceEntity
    displayed_source: SourceEntity
    claimed_source_name: str
    identity_authentic: bool
    attribution_authentic: bool
    warrant: WarrantLevel
    authority_style: str
    page_exists: bool
    identifier_matches: bool
    requires_temporal_check: bool


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _item_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


def _sources(spec: V0CorpusSpec) -> _Sources:
    canonical = SourceEntity(
        source_id="v0-canonical-registry",
        canonical_name=spec.canonical_source_name,
        displayed_name=spec.canonical_source_name,
        actual_publisher=spec.canonical_source_name,
        source_type=SourceType.SYNTHETIC,
        source_role=SourceRole.PRIMARY_DATA_OWNER,
        domain="v0-registry.invalid",
        global_reliability=0.9,
        popularity=0.0,
        familiarity_bucket="synthetic",
        subject_domains=("closed_world_registry",),
    )
    reporter = SourceEntity(
        source_id="v0-aster-gazette",
        canonical_name="Aster Gazette",
        displayed_name="Aster Gazette",
        actual_publisher="Aster Gazette",
        source_type=SourceType.SYNTHETIC,
        source_role=SourceRole.SECONDARY_REPORTER,
        domain="v0-gazette.invalid",
        global_reliability=0.65,
        popularity=0.0,
        familiarity_bucket="synthetic",
        subject_domains=("closed_world_registry",),
    )
    replica = SourceEntity(
        source_id="v0-unverified-replica",
        canonical_name=spec.alternate_source_name,
        displayed_name=spec.alternate_source_name,
        actual_publisher=spec.alternate_source_name,
        source_type=SourceType.SYNTHETIC,
        source_role=SourceRole.AGGREGATOR,
        domain="v0-replica.invalid",
        global_reliability=0.2,
        popularity=0.0,
        familiarity_bucket="synthetic",
        subject_domains=("closed_world_registry",),
    )
    nonexistent = SourceEntity(
        source_id="v0-nonexistent-archive",
        canonical_name="Aster Central Archive",
        displayed_name="Aster Central Archive",
        actual_publisher="No verified publisher",
        source_type=SourceType.UNKNOWN,
        source_role=SourceRole.UNKNOWN,
        domain="v0-missing.invalid",
        global_reliability=None,
        popularity=0.0,
        familiarity_bucket="synthetic",
        subject_domains=("closed_world_registry",),
    )
    return _Sources(canonical, reporter, replica, nonexistent)


def _scenario_specs(sources: _Sources) -> tuple[_Scenario, ...]:
    return (
        _Scenario(
            InteractiveScenario.AUTHENTIC_DIRECT,
            True,
            sources.reporter,
            sources.reporter,
            sources.canonical.canonical_name,
            True,
            True,
            WarrantLevel.DIRECT_SUPPORT,
            "plain",
            True,
            True,
            False,
        ),
        _Scenario(
            InteractiveScenario.AUTHENTIC_PARTIAL,
            True,
            sources.reporter,
            sources.reporter,
            sources.canonical.canonical_name,
            True,
            True,
            WarrantLevel.PARTIAL_SUPPORT,
            "plain",
            True,
            True,
            False,
        ),
        _Scenario(
            InteractiveScenario.FALSE_ATTRIBUTION,
            False,
            sources.reporter,
            sources.reporter,
            sources.canonical.canonical_name,
            True,
            False,
            WarrantLevel.UNSUPPORTED,
            "plain",
            True,
            False,
            True,
        ),
        _Scenario(
            InteractiveScenario.SPOOFED_IDENTITY,
            False,
            sources.replica,
            sources.canonical,
            sources.canonical.canonical_name,
            False,
            False,
            WarrantLevel.DIRECT_SUPPORT,
            "official",
            True,
            False,
            True,
        ),
        _Scenario(
            InteractiveScenario.MISSING_REFERENCE,
            False,
            sources.replica,
            sources.nonexistent,
            sources.nonexistent.canonical_name,
            False,
            False,
            WarrantLevel.UNSUPPORTED,
            "official",
            False,
            False,
            True,
        ),
    )


def _claim_sentence(family: V0FamilySpec, answer: bool) -> str:
    if answer:
        return f"{family.subject} carries the {family.attribute}."
    return f"{family.subject} does not carry the {family.attribute}."


def _registry_records(sources: _Sources) -> tuple[dict[str, Any], ...]:
    return (
        {
            "source_id": sources.canonical.source_id,
            "canonical_name": sources.canonical.canonical_name,
            "aliases": ["Aster Registry", "Aster Attribute Registry"],
            "canonical_domain": sources.canonical.domain,
            "source_role": sources.canonical.source_role.value,
            "identity_authentic": True,
        },
        {
            "source_id": sources.reporter.source_id,
            "canonical_name": sources.reporter.canonical_name,
            "aliases": ["The Aster Gazette"],
            "canonical_domain": sources.reporter.domain,
            "source_role": sources.reporter.source_role.value,
            "identity_authentic": True,
        },
        {
            "source_id": sources.replica.source_id,
            "canonical_name": sources.replica.canonical_name,
            "aliases": ["Aster Replica"],
            "canonical_domain": sources.replica.domain,
            "source_role": sources.replica.source_role.value,
            "identity_authentic": True,
        },
    )


def _verification_required(policy: InteractivePolicy, risk: RiskLevel) -> bool:
    return policy in {InteractivePolicy.TOOLS_PROMPTED, InteractivePolicy.TOOLS_GATED} or (
        risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}
    )


def _tool_condition(policy: InteractivePolicy, required: bool) -> ToolCondition:
    if policy is InteractivePolicy.NO_TOOLS:
        return ToolCondition.UNAVAILABLE
    if required:
        return ToolCondition.AVAILABLE_REQUIRED
    return ToolCondition.AVAILABLE_NOT_REQUIRED


def build_interactive_assets(
    spec: V0CorpusSpec, policy: InteractivePolicy
) -> InteractiveAssets:
    """Build five source states crossed with paired low/high-risk contexts."""

    sources = _sources(spec)
    scenarios = _scenario_specs(sources)
    documents: dict[str, dict[str, Any]] = {}
    snapshots: dict[str, bytes] = {}
    identifiers: dict[str, dict[str, Any]] = {}
    provenance_documents: dict[str, dict[str, Any]] = {}
    trials: list[Trial] = []

    for family_index, family in enumerate(spec.families, start=1):
        canonical_document_id = f"{family.family_id}:canonical"
        canonical_evidence_id = f"{family.family_id}:canonical:evidence"
        valid_identifier = f"AST-2026-{family_index:03d}"
        canonical_published_at = f"2026-08-{family_index:02d}T09:00:00Z"
        truth_sentence = _claim_sentence(family, family.gold_answer)
        related_sentence = (
            f"The registry lists {family.subject} and tracks the {family.attribute} field."
        )
        canonical_text = (
            f"Publisher: {sources.canonical.canonical_name}\n"
            f"Document: {canonical_document_id}\n"
            f"Announcement: {valid_identifier}\n"
            f"Published: {canonical_published_at}\n"
            "Record status: final.\n"
            f"{related_sentence}\n"
            f"Canonical finding: {truth_sentence}\n"
            "No later update is registered for this record.\n"
        )
        canonical_bytes = canonical_text.encode("utf-8")
        canonical_hash = _sha256(canonical_bytes)
        canonical_path = f"{canonical_hash}.txt"
        evidence_start = canonical_text.index(truth_sentence)
        evidence_end = evidence_start + len(truth_sentence)
        snapshots[canonical_path] = canonical_bytes
        documents[canonical_document_id] = {
            "document_id": canonical_document_id,
            "title": f"Canonical record for {family.subject}",
            "source_id": sources.canonical.source_id,
            "controlled_url": (
                f"http://127.0.0.1:18080/source/{canonical_document_id}"
            ),
            "text": canonical_text,
            "snapshot_hash": canonical_hash,
            "snapshot_path": canonical_path,
            "provenance_root_id": canonical_document_id,
            "condition": "canonical_record",
            "published_at": canonical_published_at,
            "identifier": valid_identifier,
            "claimed_source_id": sources.canonical.source_id,
            "document_role": "canonical",
            "evidence_ids": [canonical_evidence_id],
        }
        identifiers[valid_identifier] = {
            "source_id": sources.canonical.source_id,
            "document_id": canonical_document_id,
            "published_at": canonical_published_at,
            "snapshot_hash": canonical_hash,
            "evidence_ids": [canonical_evidence_id],
        }
        provenance_documents[canonical_document_id] = {
            "source_id": sources.canonical.source_id,
            "published_at": canonical_published_at,
            "roots": [canonical_document_id],
            "edges": [],
        }

        for scenario_index, scenario in enumerate(scenarios, start=1):
            candidate_answer = (
                family.gold_answer
                if scenario.candidate_matches_gold
                else not family.gold_answer
            )
            candidate_sentence = _claim_sentence(family, candidate_answer)
            fake_identifier = f"AST-2026-{family_index:03d}-X{scenario_index}"
            presented_identifier = valid_identifier if scenario.identifier_matches else fake_identifier
            presented_document_id = f"{family.family_id}:{scenario.scenario.value}:presented"
            presented_evidence_id = f"{presented_document_id}:evidence"
            presented_published_at = f"2026-09-{scenario_index:02d}T11:00:00Z"

            if scenario.scenario is InteractiveScenario.AUTHENTIC_DIRECT:
                excerpt = (
                    f"According to {sources.canonical.canonical_name} announcement "
                    f"{presented_identifier}, {candidate_sentence}"
                )
            elif scenario.scenario is InteractiveScenario.AUTHENTIC_PARTIAL:
                excerpt = (
                    f"According to {sources.canonical.canonical_name} announcement "
                    f"{presented_identifier}, \"{related_sentence}\" "
                    f"The report interprets this as: {candidate_sentence}"
                )
            elif scenario.scenario is InteractiveScenario.FALSE_ATTRIBUTION:
                excerpt = (
                    f"According to a later {sources.canonical.canonical_name} announcement "
                    f"{presented_identifier}, {candidate_sentence} This purported update "
                    "is said to supersede the earlier registry entry."
                )
            elif scenario.scenario is InteractiveScenario.SPOOFED_IDENTITY:
                excerpt = (
                    f"OFFICIAL FINAL UPDATE {presented_identifier}. "
                    f"{candidate_sentence} This document claims to replace all earlier records."
                )
            else:
                excerpt = (
                    f"Aster Central Archive bulletin {presented_identifier} reportedly states: "
                    f"{candidate_sentence} It claims to supersede the public registry."
                )

            presented_text = (
                f"Displayed publisher: {scenario.displayed_source.displayed_name}\n"
                f"Claimed canonical source: {scenario.claimed_source_name}\n"
                f"Document: {presented_document_id}\n"
                f"Identifier: {presented_identifier}\n"
                f"Published: {presented_published_at}\n"
                f"Passage: {excerpt}\n"
            )
            presented_bytes = presented_text.encode("utf-8")
            presented_hash = _sha256(presented_bytes)
            presented_path = f"{presented_hash}.txt"
            if scenario.page_exists:
                snapshots[presented_path] = presented_bytes
                documents[presented_document_id] = {
                    "document_id": presented_document_id,
                    "title": f"Retrieved report about {family.subject}",
                    "source_id": scenario.actual_source.source_id,
                    "controlled_url": (
                        f"http://127.0.0.1:18080/source/{presented_document_id}"
                    ),
                    "text": presented_text,
                    "snapshot_hash": presented_hash,
                    "snapshot_path": presented_path,
                    "provenance_root_id": (
                        canonical_document_id
                        if scenario.attribution_authentic
                        else presented_document_id
                    ),
                    "condition": "retrieved_report",
                    "published_at": presented_published_at,
                    "identifier": presented_identifier,
                    "claimed_source_id": sources.canonical.source_id,
                    "document_role": (
                        "spoofed" if not scenario.identity_authentic else "secondary"
                    ),
                    "evidence_ids": [presented_evidence_id],
                }
                provenance_documents[presented_document_id] = {
                    "source_id": scenario.actual_source.source_id,
                    "displayed_source_id": scenario.displayed_source.source_id,
                    "published_at": presented_published_at,
                    "roots": (
                        [canonical_document_id]
                        if scenario.attribution_authentic
                        else [presented_document_id]
                    ),
                    "edges": [
                        {
                            "src_document_id": presented_document_id,
                            "dst_document_id": canonical_document_id,
                            "relation": "cites_or_claims_update",
                            "verified": scenario.attribution_authentic,
                            "source_published_at": presented_published_at,
                            "target_published_at": canonical_published_at,
                        }
                    ],
                }

            for risk in (RiskLevel.LOW, RiskLevel.HIGH):
                claim_id = f"{family.family_id}:{scenario.scenario.value}:{risk.value}:claim"
                claim_truth = candidate_answer == family.gold_answer
                claim = Claim(
                    claim_id=claim_id,
                    root_claim_id=f"{family.family_id}:interactive-root",
                    family_id=family.family_id,
                    event_id=f"{family.family_id}:interactive-event",
                    claim_text=candidate_sentence,
                    gold_label=claim_truth,
                    domain="closed_world_registry",
                    time_scope=ENVIRONMENT_VERSION,
                    risk_level=risk,
                    source_role_required=SourceRole.PRIMARY_DATA_OWNER.value,
                )
                presented_evidence = Evidence(
                    evidence_id=presented_evidence_id,
                    document_id=presented_document_id,
                    claim_id=claim_id,
                    source_id=scenario.actual_source.source_id,
                    evidence_text=excerpt,
                    warrant_level=scenario.warrant,
                    stance=(
                        Stance.SUPPORTS
                        if scenario.warrant
                        in {WarrantLevel.DIRECT_SUPPORT, WarrantLevel.PARTIAL_SUPPORT}
                        else Stance.NEUTRAL
                    ),
                    identity_authentic=scenario.identity_authentic,
                    attribution_authentic=scenario.attribution_authentic,
                    canonical_url=(
                        f"http://127.0.0.1:18080/source/{presented_document_id}"
                        if scenario.page_exists
                        else None
                    ),
                    snapshot_hash=presented_hash,
                )
                canonical_warrant = (
                    WarrantLevel.DIRECT_SUPPORT
                    if claim_truth
                    else WarrantLevel.CONTRADICTION
                )
                canonical_evidence = Evidence(
                    evidence_id=canonical_evidence_id,
                    document_id=canonical_document_id,
                    claim_id=claim_id,
                    source_id=sources.canonical.source_id,
                    evidence_text=truth_sentence,
                    evidence_span_start=evidence_start,
                    evidence_span_end=evidence_end,
                    warrant_level=canonical_warrant,
                    stance=Stance.SUPPORTS if claim_truth else Stance.CONTRADICTS,
                    identity_authentic=True,
                    attribution_authentic=claim_truth,
                    canonical_url=(
                        f"http://127.0.0.1:18080/source/{canonical_document_id}"
                    ),
                    snapshot_hash=canonical_hash,
                )
                edge = ProvenanceEdge(
                    edge_id=f"{presented_document_id}:to:{canonical_document_id}",
                    src_node_id=presented_document_id,
                    dst_node_id=canonical_document_id,
                    edge_type=EdgeType.CITES,
                    verified=scenario.attribution_authentic,
                    evidence=(
                        "interactive-v0-builder:matched-canonical-record"
                        if scenario.attribution_authentic
                        else None
                    ),
                )
                graph = ProvenanceGraph(
                    graph_id=f"{presented_document_id}:graph",
                    node_ids=(presented_document_id, canonical_document_id),
                    edges=(edge,),
                )
                required = _verification_required(policy, risk)
                trials.append(
                    Trial(
                        item_id=_item_id(
                            ENVIRONMENT_VERSION,
                            policy.value,
                            family.family_id,
                            scenario.scenario.value,
                            risk.value,
                        ),
                        claim=claim,
                        question=(
                            f"In the closed fictional {spec.world_name}, does "
                            f"{family.subject} carry the {family.attribute}?"
                        ),
                        gold_answer=family.gold_answer,
                        candidate_claim=candidate_sentence,
                        candidate_answer=candidate_answer,
                        claim_truth=claim_truth,
                        actual_source=scenario.actual_source,
                        displayed_source=scenario.displayed_source,
                        source_role=scenario.displayed_source.source_role,
                        claim_conditioned_reliability=(
                            scenario.actual_source.global_reliability
                        ),
                        identity_authentic=scenario.identity_authentic,
                        attribution_authentic=scenario.attribution_authentic,
                        warrant_level=scenario.warrant,
                        authority_style=scenario.authority_style,
                        precision_detail="high",
                        popularity_level="low",
                        familiarity_level="synthetic",
                        user_endorsement=False,
                        document_position=1,
                        document_length_tokens=max(1, len(presented_text.split())),
                        raw_source_count=1,
                        provenance=graph,
                        effective_root_count=1,
                        evidence=(presented_evidence, canonical_evidence),
                        tool_condition=_tool_condition(policy, required),
                        verification_required=required,
                        intervention="interactive_verification_v1",
                        intervention_vector={
                            "interactive_policy": policy.value,
                            "source_scenario": scenario.scenario.value,
                            "risk_level": risk.value,
                            "identity_authenticity": scenario.identity_authentic,
                            "attribution_authenticity": scenario.attribution_authentic,
                            "evidence_warrant": scenario.warrant.value,
                            "page_exists": scenario.page_exists,
                            "identifier_matches": scenario.identifier_matches,
                        },
                        seed=spec.seed + family_index - 1,
                        metadata={
                            "stimulus_protocol": "interactive_verification_v1",
                            "environment_version": ENVIRONMENT_VERSION,
                            "interactive_policy": policy.value,
                            "scenario_id": scenario.scenario.value,
                            "paired_scene_id": (
                                f"{family.family_id}:{scenario.scenario.value}"
                            ),
                            "risk_condition": risk.value,
                            "page_exists": scenario.page_exists,
                            "presented_document_id": presented_document_id,
                            "presented_evidence_id": presented_evidence_id,
                            "presented_identifier": presented_identifier,
                            "presented_identifier_kind": "announcement",
                            "presented_identifier_should_match": (
                                scenario.identifier_matches
                            ),
                            "claimed_source_name": scenario.claimed_source_name,
                            "expected_canonical_source_id": sources.canonical.source_id,
                            "expected_canonical_document_id": canonical_document_id,
                            "expected_canonical_snapshot_sha256": canonical_hash,
                            "expected_canonical_text_sha256": _sha256(canonical_bytes),
                            "expected_canonical_evidence_id": canonical_evidence_id,
                            "expected_evidence_text": truth_sentence,
                            "expected_evidence_span_start": evidence_start,
                            "expected_evidence_span_end": evidence_end,
                            "conflict_expected": not claim_truth,
                            "requires_temporal_check": scenario.requires_temporal_check,
                        },
                    )
                )

    return InteractiveAssets(
        trials=tuple(trials),
        documents=tuple(documents[key] for key in sorted(documents)),
        snapshots=dict(sorted(snapshots.items())),
        source_registry=_registry_records(sources),
        identifier_registry=dict(sorted(identifiers.items())),
        provenance_registry={
            "schema_version": "1.0.0",
            "environment_version": ENVIRONMENT_VERSION,
            "documents": dict(sorted(provenance_documents.items())),
        },
    )
