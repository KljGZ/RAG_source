"""Deterministic closed-world V0 family construction."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, ConfigDict, Field, model_validator

from provtrust.datasets.synthetic_builder import FactorialDesign, SyntheticSeed, build_factorial
from provtrust.schemas.claim import Claim, RiskLevel
from provtrust.schemas.source import SourceEntity, SourceRole, SourceType
from provtrust.schemas.trial import Trial


class V0FamilySpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    family_id: str = Field(pattern=r"^v0-family-[0-9]{3}$")
    subject: str = Field(min_length=1)
    attribute: str = Field(min_length=1)
    gold_answer: bool
    candidate_answer: bool


class V0CorpusSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    dataset_id: str = Field(min_length=1)
    builder_version: str = "paired-static-v1"
    purpose: str = Field(min_length=1)
    license: str = "Apache-2.0"
    redistributable: bool = True
    contains_real_world_claims: bool = False
    seed: int = Field(ge=0)
    world_name: str = Field(min_length=1)
    canonical_source_name: str = Field(min_length=1)
    alternate_source_name: str = Field(min_length=1)
    design: FactorialDesign = Field(default_factory=FactorialDesign)
    families: tuple[V0FamilySpec, ...] = Field(min_length=4)

    @model_validator(mode="after")
    def validate_closed_balanced_corpus(self) -> V0CorpusSpec:
        if self.contains_real_world_claims:
            raise ValueError("V0 closed-world corpus cannot contain real-world claims")
        family_ids = [family.family_id for family in self.families]
        if len(family_ids) != len(set(family_ids)):
            raise ValueError("V0 family identifiers must be unique")
        subject_attributes = [(family.subject, family.attribute) for family in self.families]
        if len(subject_attributes) != len(set(subject_attributes)):
            raise ValueError("V0 subject/attribute pairs must be unique")
        combinations = Counter(
            (family.gold_answer, family.candidate_answer) for family in self.families
        )
        if len(combinations) != 4 or len(set(combinations.values())) != 1:
            raise ValueError("gold and candidate boolean combinations must be exactly balanced")
        if self.design.design != "paired":
            raise ValueError("the V0 identified corpus requires the paired design")
        return self


def _claim_text(family: V0FamilySpec) -> str:
    if family.candidate_answer:
        return f"{family.subject} carries the {family.attribute}."
    return f"{family.subject} does not carry the {family.attribute}."


def _opposite_claim_text(family: V0FamilySpec) -> str:
    if family.candidate_answer:
        return f"{family.subject} does not carry the {family.attribute}."
    return f"{family.subject} carries the {family.attribute}."


def build_v0_corpus(spec: V0CorpusSpec) -> tuple[Trial, ...]:
    authentic_source = SourceEntity(
        source_id="v0-canonical-registry",
        canonical_name=spec.canonical_source_name,
        displayed_name=spec.canonical_source_name,
        actual_publisher=spec.canonical_source_name,
        source_type=SourceType.SYNTHETIC,
        source_role=SourceRole.PRIMARY_DATA_OWNER,
        domain="v0-registry.invalid",
        global_reliability=max(spec.design.reliability),
        popularity=0.0,
        familiarity_bucket="synthetic",
        subject_domains=("closed_world_registry",),
    )
    alternate_source = SourceEntity(
        source_id="v0-unverified-replica",
        canonical_name=spec.alternate_source_name,
        displayed_name=spec.alternate_source_name,
        actual_publisher=spec.alternate_source_name,
        source_type=SourceType.SYNTHETIC,
        source_role=SourceRole.AGGREGATOR,
        domain="v0-replica.invalid",
        global_reliability=min(spec.design.reliability),
        popularity=0.0,
        familiarity_bucket="synthetic",
        subject_domains=("closed_world_registry",),
    )
    trials: list[Trial] = []
    for index, family in enumerate(spec.families):
        candidate_claim = _claim_text(family)
        candidate_truth = family.candidate_answer == family.gold_answer
        claim = Claim(
            claim_id=f"{family.family_id}:claim",
            root_claim_id=f"{family.family_id}:root-claim",
            family_id=family.family_id,
            event_id=f"{family.family_id}:event",
            claim_text=candidate_claim,
            gold_label=candidate_truth,
            domain="closed_world_registry",
            time_scope=spec.builder_version,
            risk_level=RiskLevel.LOW,
            source_role_required=SourceRole.PRIMARY_DATA_OWNER.value,
        )
        seed = SyntheticSeed(
            claim=claim,
            question=(
                f"In the closed fictional {spec.world_name}, does {family.subject} "
                f"carry the {family.attribute}?"
            ),
            gold_answer=family.gold_answer,
            candidate_claim=candidate_claim,
            candidate_answer=family.candidate_answer,
            claim_truth=candidate_truth,
            authentic_source=authentic_source,
            alternate_source=alternate_source,
            direct_evidence_text=(
                f"The canonical {spec.world_name} entry states: {candidate_claim}"
            ),
            related_evidence_text=(
                f"The canonical {spec.world_name} contains an entry for {family.subject} "
                f"and tracks attributes, but this passage does not state whether it carries "
                f"the {family.attribute}."
            ),
            contradiction_text=(
                f"The canonical {spec.world_name} entry states: "
                f"{_opposite_claim_text(family)}"
            ),
        )
        trials.extend(build_factorial(seed, spec.design, seed_value=spec.seed + index))
    return tuple(trials)
