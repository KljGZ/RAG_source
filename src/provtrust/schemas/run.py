"""Immutable model, attempt, result, and run records."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from provtrust.schemas.tool_event import ToolEvent


class ParseStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class ModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    model: str
    model_revision: str | None = None
    observed_at: datetime
    temperature: float = Field(ge=0.0)
    max_tokens: int = Field(gt=0)
    system_prompt_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: str

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("model observation timestamp must be timezone-aware")
        return value


class AttemptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt: int = Field(ge=0)
    started_at: datetime
    completed_at: datetime
    raw_output_path: str
    raw_output_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    parse_status: ParseStatus
    parsed: dict[str, Any] | None = None
    error_type: str | None = None
    retry_reason: str | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_timing(self) -> AttemptRecord:
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("attempt timestamps must be timezone-aware")
        if self.started_at > self.completed_at:
            raise ValueError("attempt completion precedes its start")
        if self.parse_status is ParseStatus.FAILED and not self.error_type:
            raise ValueError("failed parse requires error_type")
        return self


class TrialResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    run_id: str
    item_id: str
    model: ModelSpec
    attempts: tuple[AttemptRecord, ...]
    selected_attempt: int | None
    answer: bool | str | float | None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    declared_factors: dict[str, float] = Field(default_factory=dict)
    cited_evidence_ids: tuple[str, ...] = ()
    tool_trace: tuple[ToolEvent, ...] = ()
    abstained: bool = False
    claimed_verified: bool = False

    @model_validator(mode="after")
    def validate_selection(self) -> TrialResult:
        attempt_ids = {attempt.attempt for attempt in self.attempts}
        if self.selected_attempt is not None and self.selected_attempt not in attempt_ids:
            raise ValueError("selected attempt is missing")
        if not self.abstained and self.answer is None:
            raise ValueError("non-abstaining result requires an answer")
        return self


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    git_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    experiment_plan_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_specs: tuple[ModelSpec, ...]
    seeds: tuple[int, ...]
    shard_count: int = Field(gt=0)
    environment_lock_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: str = "created"
