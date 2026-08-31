"""Evidence support and authenticity schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WarrantLevel(StrEnum):
    DIRECT_SUPPORT = "direct_support"
    PARTIAL_SUPPORT = "partial_support"
    RELATED_ONLY = "related_only"
    UNSUPPORTED = "unsupported"
    CONTRADICTION = "contradiction"


class Stance(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


class Evidence(BaseModel):
    """A frozen claim-document relation with a content-addressed snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    evidence_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    evidence_text: str = Field(min_length=1)
    evidence_span_start: int | None = Field(default=None, ge=0)
    evidence_span_end: int | None = Field(default=None, ge=0)
    warrant_level: WarrantLevel
    stance: Stance
    identity_authentic: bool
    attribution_authentic: bool
    canonical_url: str | None = None
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence_relation(self) -> Evidence:
        if (self.evidence_span_start is None) != (self.evidence_span_end is None):
            raise ValueError("evidence span endpoints must be both present or both absent")
        if (
            self.evidence_span_start is not None
            and self.evidence_span_end is not None
            and self.evidence_span_start >= self.evidence_span_end
        ):
            raise ValueError("evidence span must be non-empty")
        if self.attribution_authentic and not self.identity_authentic:
            raise ValueError("authentic attribution requires an authentic source identity")
        if self.warrant_level is WarrantLevel.CONTRADICTION and self.stance is not Stance.CONTRADICTS:
            raise ValueError("contradiction warrant requires contradicts stance")
        return self
