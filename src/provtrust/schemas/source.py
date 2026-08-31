"""Source identity and role schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceType(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    AGGREGATOR = "aggregator"
    SOCIAL = "social"
    SYNTHETIC = "synthetic"
    UNKNOWN = "unknown"


class SourceRole(StrEnum):
    PRIMARY_REGULATOR = "primary_regulator"
    PRIMARY_DATA_OWNER = "primary_data_owner"
    PRIMARY_AUTHOR = "primary_author"
    NEWSWIRE = "newswire"
    SECONDARY_REPORTER = "secondary_reporter"
    AGGREGATOR = "aggregator"
    COMMENTATOR = "commentator"
    UNKNOWN = "unknown"


class SourceEntity(BaseModel):
    """Canonical source identity separated from its displayed identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    source_id: str = Field(min_length=1)
    canonical_name: str = Field(min_length=1)
    displayed_name: str = Field(min_length=1)
    actual_publisher: str = Field(min_length=1)
    source_type: SourceType
    source_role: SourceRole = SourceRole.UNKNOWN
    domain: str | None = None
    global_reliability: float | None = Field(default=None, ge=0.0, le=1.0)
    popularity: float | None = Field(default=None, ge=0.0, le=1.0)
    familiarity_bucket: str | None = None
    subject_domains: tuple[str, ...] = ()
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    @model_validator(mode="after")
    def validate_time_interval(self) -> SourceEntity:
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("valid_from must not be after valid_to")
        return self
