"""Canonical factorial trial schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from provtrust.schemas.claim import Claim
from provtrust.schemas.evidence import Evidence, WarrantLevel
from provtrust.schemas.provenance import ProvenanceGraph
from provtrust.schemas.source import SourceEntity, SourceRole


class Trial(BaseModel):
    """One counterfactual variant; variants share a family_id."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    item_id: str = Field(min_length=1)
    claim: Claim
    question: str = Field(min_length=1)
    gold_answer: bool | str | float
    candidate_claim: str = Field(min_length=1)
    claim_truth: bool | None
    actual_source: SourceEntity
    displayed_source: SourceEntity
    source_role: SourceRole
    claim_conditioned_reliability: float | None = Field(default=None, ge=0.0, le=1.0)
    identity_authentic: bool
    attribution_authentic: bool
    warrant_level: WarrantLevel
    authority_style: str
    precision_detail: str = "matched"
    popularity_level: str
    familiarity_level: str = "matched"
    user_endorsement: bool
    document_position: int = Field(ge=1)
    document_length_tokens: int = Field(ge=1)
    raw_source_count: int = Field(default=1, ge=1)
    provenance: ProvenanceGraph
    effective_root_count: int = Field(ge=1)
    evidence: tuple[Evidence, ...]
    verification_required: bool = False
    intervention: str = Field(min_length=1)
    seed: int = Field(ge=0)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @property
    def family_id(self) -> str:
        return self.claim.family_id

    @property
    def event_id(self) -> str | None:
        return self.claim.event_id

    @property
    def root_claim_id(self) -> str:
        return self.claim.root_claim_id

    @model_validator(mode="after")
    def validate_trial_invariants(self) -> Trial:
        if self.attribution_authentic and not self.identity_authentic:
            raise ValueError("authentic attribution requires authentic identity")
        if self.attribution_authentic and self.actual_source.source_id != self.displayed_source.source_id:
            raise ValueError("authentic attribution cannot swap the displayed source")
        if self.effective_root_count > self.raw_source_count:
            raise ValueError("effective roots cannot exceed raw sources")
        if self.effective_root_count != len(self.provenance.roots()):
            raise ValueError("effective_root_count must equal the provenance graph root count")
        for evidence in self.evidence:
            if evidence.claim_id != self.claim.claim_id:
                raise ValueError("evidence must refer to the trial claim")
        return self
