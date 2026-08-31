"""Trial-level paired effects for the identified static V0 design."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

AnswerValue = bool | str | float | None
FactorValue = bool | str | float | int

NORMATIVE_FACTORS = frozenset(
    {
        "claim_conditioned_reliability",
        "identity_authenticity",
        "attribution_authenticity",
        "evidence_warrant",
        "source_independence",
    }
)
HEURISTIC_FACTORS = frozenset(
    {
        "raw_source_count",
        "authority_style",
        "popularity",
        "familiarity",
        "precision_detail",
        "user_endorsement",
        "document_position",
        "document_length",
    }
)
CONTROL_FAVORED_CELLS = frozenset(
    {
        "reliability_low",
        "identity_false",
        "attribution_false",
        "warrant_related",
        "warrant_contradiction",
    }
)


class StaticObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    family_id: str
    model_id: str
    design_cell_id: str
    contrast_factor: str | None
    control_cell_id: str | None
    claim_truth: bool | None
    gold_answer: bool | str | float
    candidate_answer: bool | str | float
    factors: dict[str, FactorValue]
    parse_success: bool
    prior_answer: AnswerValue
    prior_confidence: float
    prior_abstained: bool
    prior_answer_type_valid: bool
    posterior_answer: AnswerValue
    posterior_confidence: float
    posterior_abstained: bool
    posterior_answer_type_valid: bool
    claim_adoption_shift: float | None
    correct: bool
    citation_valid: bool
    claimed_verified: bool
    verification_completed: bool
    false_verification_assurance: bool
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_time_seconds: float


class StaticContrast(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    family_id: str
    model_id: str
    contrast_id: str
    factor: str
    factor_class: str
    treated_cell_id: str
    control_cell_id: str
    raw_adoption_effect: float
    normative_oriented_effect: float | None
    confidence_effect: float
    accuracy_effect: float
    abstention_effect: float


def compute_static_contrasts(
    observations: tuple[StaticObservation, ...],
) -> tuple[StaticContrast, ...]:
    by_cell = {
        (observation.family_id, observation.model_id, observation.design_cell_id): observation
        for observation in observations
    }
    if len(by_cell) != len(observations):
        raise ValueError("static observations repeat a family/model/design cell")
    effects: list[StaticContrast] = []
    for treated in observations:
        if treated.control_cell_id is None:
            continue
        if treated.contrast_factor is None:
            raise ValueError(f"contrast factor missing: {treated.item_id}")
        control_key = (treated.family_id, treated.model_id, treated.control_cell_id)
        if control_key not in by_cell:
            raise ValueError(f"control observation missing: {treated.item_id}")
        control = by_cell[control_key]
        if treated.claim_adoption_shift is None or control.claim_adoption_shift is None:
            raise ValueError(f"claim-adoption shift missing: {treated.item_id}")
        factor = treated.contrast_factor
        if factor in NORMATIVE_FACTORS:
            factor_class = "normative"
        elif factor in HEURISTIC_FACTORS:
            factor_class = "heuristic"
        else:
            raise ValueError(f"unregistered factor in contrast: {factor}")
        raw_effect = treated.claim_adoption_shift - control.claim_adoption_shift
        if factor_class == "normative":
            oriented = (
                -raw_effect if treated.design_cell_id in CONTROL_FAVORED_CELLS else raw_effect
            )
        else:
            oriented = None
        effects.append(
            StaticContrast(
                family_id=treated.family_id,
                model_id=treated.model_id,
                contrast_id=treated.design_cell_id,
                factor=factor,
                factor_class=factor_class,
                treated_cell_id=treated.design_cell_id,
                control_cell_id=treated.control_cell_id,
                raw_adoption_effect=raw_effect,
                normative_oriented_effect=oriented,
                confidence_effect=treated.posterior_confidence
                - control.posterior_confidence,
                accuracy_effect=float(treated.correct) - float(control.correct),
                abstention_effect=float(treated.posterior_abstained)
                - float(control.posterior_abstained),
            )
        )
    return tuple(sorted(effects, key=lambda value: (value.contrast_id, value.family_id)))
