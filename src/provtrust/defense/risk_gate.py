"""Frozen, inspectable high-risk verification gate."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RiskFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    conflict: float = Field(ge=0.0, le=1.0)
    unfamiliarity: float = Field(ge=0.0, le=1.0)
    high_stakes: float = Field(ge=0.0, le=1.0)
    attribution_anomaly: float = Field(ge=0.0, le=1.0)
    source_dependence: float = Field(ge=0.0, le=1.0)
    prior_conflict: float = Field(ge=0.0, le=1.0)


class RiskWeights(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    conflict: float = 1.0
    unfamiliarity: float = 0.5
    high_stakes: float = 1.0
    attribution_anomaly: float = 1.0
    source_dependence: float = 0.75
    prior_conflict: float = 0.75
    threshold: float = Field(default=1.5, ge=0.0)


class RiskAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    score: float
    threshold: float
    verification_required: bool
    contributions: dict[str, float]


class RiskGate:
    def __init__(self, weights: RiskWeights) -> None:
        self.weights = weights

    def assess(self, features: RiskFeatures) -> RiskAssessment:
        values = features.model_dump()
        weight_values = self.weights.model_dump(exclude={"threshold"})
        contributions = {
            name: float(values[name]) * float(weight_values[name]) for name in values
        }
        score = sum(contributions.values())
        return RiskAssessment(
            score=score,
            threshold=self.weights.threshold,
            verification_required=score > self.weights.threshold,
            contributions=contributions,
        )
