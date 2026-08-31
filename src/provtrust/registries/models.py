"""Frozen model configuration registry with role separation checks."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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
