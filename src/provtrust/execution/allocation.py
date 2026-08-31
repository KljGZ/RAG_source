"""Reviewed resource-allocation contracts for experiment execution."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ResourceRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cpu_cores: int = Field(ge=1)
    ram_gib: float = Field(gt=0.0)
    storage_gib: float = Field(gt=0.0)
    gpu_count: int = Field(ge=0)
    minimum_gpu_memory_gib: float = Field(default=0.0, ge=0.0)
    estimated_gpu_hours: float = Field(default=0.0, ge=0.0)
    api_budget_usd: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_gpu_requirements(self) -> ResourceRequirements:
        if self.gpu_count == 0 and (
            self.minimum_gpu_memory_gib > 0.0 or self.estimated_gpu_hours > 0.0
        ):
            raise ValueError("GPU memory/hours require at least one GPU")
        return self


class ResourceAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    allocation_id: str = Field(min_length=1)
    approved: bool
    approved_by: str = Field(min_length=1)
    approved_at: datetime
    expires_at: datetime
    stage: str = Field(min_length=1)
    host: str = Field(min_length=1)
    cpu_cores: tuple[int, ...]
    ram_gib: float = Field(gt=0.0)
    storage_gib: float = Field(gt=0.0)
    gpu_indices: tuple[int, ...] = ()
    gpu_model: str | None = None
    gpu_memory_gib_each: float = Field(default=0.0, ge=0.0)
    gpu_hours: float = Field(default=0.0, ge=0.0)
    api_budget_usd: float = Field(default=0.0, ge=0.0)
    api_providers: tuple[str, ...] = ()
    notes: str = ""

    @field_validator("approved_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("allocation timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_allocation(self) -> ResourceAllocation:
        if self.expires_at <= self.approved_at:
            raise ValueError("allocation must expire after approval")
        if len(set(self.cpu_cores)) != len(self.cpu_cores) or any(
            value < 0 for value in self.cpu_cores
        ):
            raise ValueError("CPU core identifiers must be unique and non-negative")
        if len(set(self.gpu_indices)) != len(self.gpu_indices) or any(
            value < 0 for value in self.gpu_indices
        ):
            raise ValueError("GPU identifiers must be unique and non-negative")
        if self.gpu_indices and not self.gpu_model:
            raise ValueError("GPU allocations require a model name")
        return self

    def validate_for(
        self, requirements: ResourceRequirements, *, stage: str, now: datetime
    ) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.approved:
            errors.append("allocation_not_approved")
        if self.stage != stage:
            errors.append("allocation_stage_mismatch")
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("allocation validation time must be timezone-aware")
        if now >= self.expires_at:
            errors.append("allocation_expired")
        if len(self.cpu_cores) < requirements.cpu_cores:
            errors.append("insufficient_cpu_cores")
        if self.ram_gib < requirements.ram_gib:
            errors.append("insufficient_ram")
        if self.storage_gib < requirements.storage_gib:
            errors.append("insufficient_storage")
        if len(self.gpu_indices) < requirements.gpu_count:
            errors.append("insufficient_gpu_count")
        if (
            requirements.gpu_count
            and self.gpu_memory_gib_each < requirements.minimum_gpu_memory_gib
        ):
            errors.append("insufficient_gpu_memory")
        if self.gpu_hours < requirements.estimated_gpu_hours:
            errors.append("insufficient_gpu_hours")
        if self.api_budget_usd < requirements.api_budget_usd:
            errors.append("insufficient_api_budget")
        return tuple(errors)
