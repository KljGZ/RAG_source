"""Atomic claim schema."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Claim(BaseModel):
    """An atomic proposition whose evidence can be independently checked."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    claim_id: str = Field(min_length=1)
    root_claim_id: str = Field(min_length=1)
    family_id: str = Field(min_length=1)
    event_id: str | None = None
    claim_text: str = Field(min_length=1)
    gold_label: bool | str | float
    domain: str = Field(min_length=1)
    time_scope: str | None = None
    risk_level: RiskLevel
    source_role_required: str | None = None

    @field_validator("claim_id", "root_claim_id", "family_id", "domain")
    @classmethod
    def no_surrounding_whitespace(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("identifier fields must not contain surrounding whitespace")
        return value
