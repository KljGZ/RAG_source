"""Auditable tool-trace events."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolEventStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"
    TIMED_OUT = "timed_out"


class ToolEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    event_id: str = Field(min_length=1)
    trial_item_id: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any]
    status: ToolEventStatus
    output_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    evidence_ids: tuple[str, ...] = ()
    error_type: str | None = None
    latency_ms: float = Field(ge=0.0)

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("tool-event timestamps must be timezone-aware")
        return value
