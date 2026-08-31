"""Attribution verification against frozen snapshot metadata."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AttributionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    actual_publisher_source_id: str
    attributed_source_id: str | None
    claim_id: str
    claim_present_in_canonical_text: bool
    identifier_verified: bool
    publication_time_verified: bool
    evidence_span_ids: tuple[str, ...]


class AttributionAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    identity_authentic: bool
    attribution_authentic: bool
    completed: bool
    reasons: tuple[str, ...]
    evidence_span_ids: tuple[str, ...]


def verify_attribution(
    record: AttributionRecord, *, expected_source_id: str, expected_claim_id: str
) -> AttributionAssessment:
    reasons: list[str] = []
    identity = record.actual_publisher_source_id == expected_source_id
    if not identity:
        reasons.append("publisher_identity_mismatch")
    attribution = (
        record.attributed_source_id == expected_source_id
        and record.claim_id == expected_claim_id
        and record.claim_present_in_canonical_text
    )
    if not attribution:
        reasons.append("attribution_not_confirmed_in_canonical_text")
    completed = record.identifier_verified and record.publication_time_verified
    if not completed:
        reasons.append("identifier_or_publication_time_unverified")
    return AttributionAssessment(
        identity_authentic=identity,
        attribution_authentic=attribution,
        completed=completed,
        reasons=tuple(reasons),
        evidence_span_ids=record.evidence_span_ids,
    )
