"""Frozen model configuration registry with role separation checks."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from provtrust.registries.base import Registry


class RegisteredModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    model: str
    revision: str | None = None
    observed_at: datetime
    temperature: float = Field(ge=0.0)
    max_tokens: int = Field(gt=0)
    roles: frozenset[str]


class FrozenSnapshotReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_platform: str = Field(min_length=1)
    repository: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    captured_at: datetime
    upstream_huggingface_revision: str | None = None
    asset_manifest: str = Field(min_length=1)
    asset_manifest_sha256: str
    root_sha256: str
    file_count: int = Field(gt=0)
    total_bytes: int = Field(gt=0)

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("snapshot capture time must be timezone-aware")
        return value

    @field_validator("asset_manifest_sha256", "root_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("snapshot hashes must be lowercase SHA-256 values")
        return value


class FrozenPromptReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("prompt hash must be a lowercase SHA-256 value")
        return value


class FrozenGenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enable_thinking: bool
    do_sample: bool
    temperature: float = Field(ge=0.0)
    top_p: float = Field(gt=0.0, le=1.0)
    top_k: int = Field(gt=0)
    max_tokens: int = Field(gt=0)
    seeds: tuple[int, ...]

    @field_validator("seeds")
    @classmethod
    def validate_seeds(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("generation seeds must be nonempty and unique")
        return value

    @model_validator(mode="after")
    def validate_sampling_contract(self) -> FrozenGenerationConfig:
        if self.do_sample and self.temperature <= 0.0:
            raise ValueError("sampling requires a positive temperature")
        if not self.do_sample and self.temperature != 0.0:
            raise ValueError("deterministic decoding requires temperature zero")
        return self


class FrozenProviderAdapter(BaseModel):
    """Auditable provider compatibility layer used by a frozen registration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    adapter_id: str = Field(min_length=1)
    runtime: Literal["inspect_ai"]
    runtime_version: str = Field(min_length=1)
    registration_model_name: str = Field(min_length=1)
    model_family: str = Field(min_length=1)
    implementation_path: str = Field(min_length=1)
    implementation_sha256: str
    acceptance_path: str = Field(min_length=1)
    acceptance_sha256: str

    @field_validator("implementation_sha256", "acceptance_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("provider-adapter hashes must be lowercase SHA-256 values")
        return value


class FrozenModelRegistration(BaseModel):
    """Publication-safe model identity separate from machine-local model args."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    registration_id: str = Field(min_length=1)
    status: Literal["frozen"]
    role: Literal["target", "secondary_target", "judge"]
    primary_judge_eligible: bool
    provider: Literal["hf"]
    inspect_model: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    architecture: str = Field(min_length=1)
    license: str = Field(min_length=1)
    parameter_count_billions: float = Field(gt=0.0)
    native_context_tokens: int = Field(gt=0)
    config_max_position_embeddings: int = Field(gt=0)
    inference_dtype: Literal["bfloat16"]
    local_files_only: bool
    trust_remote_code: bool
    deployment_subdirectory: str = Field(min_length=1)
    snapshot: FrozenSnapshotReference
    generation: FrozenGenerationConfig
    system_prompt: FrozenPromptReference
    provider_adapter: FrozenProviderAdapter | None = None

    @field_validator("deployment_subdirectory")
    @classmethod
    def validate_deployment_subdirectory(cls, value: str) -> str:
        if value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("deployment_subdirectory must be one directory name")
        return value

    @model_validator(mode="after")
    def target_cannot_be_primary_judge(self) -> FrozenModelRegistration:
        if self.role != "judge" and self.primary_judge_eligible:
            raise ValueError("the first target model cannot also be a primary judge")
        return self


class ModelRegistry(Registry[RegisteredModel]):
    def validate_role_separation(self, target: str, primary_judge: str) -> None:
        target_model = self.get(target)
        judge_model = self.get(primary_judge)
        if (target_model.provider, target_model.model, target_model.revision) == (
            judge_model.provider,
            judge_model.model,
            judge_model.revision,
        ):
            raise ValueError("target model and primary judge must be different")
