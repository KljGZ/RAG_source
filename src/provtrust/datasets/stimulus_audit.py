"""Identification audit for model-visible paired counterfactual stimuli."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from pydantic import BaseModel, ConfigDict

from provtrust.schemas.trial import Trial
from provtrust.tasks.common import render_prior, render_trial

EXPECTED_VISIBLE_PATHS: dict[str, frozenset[str]] = {
    "claim_conditioned_reliability": frozenset(
        {"source_audit.claim_conditioned_reliability"}
    ),
    "identity_authenticity": frozenset({"source_audit.identity_check"}),
    "attribution_authenticity": frozenset({"source_audit.attribution_check"}),
    "evidence_warrant": frozenset({"documents"}),
    "raw_source_count": frozenset(
        {"documents", "provenance_audit.raw_supporting_pages"}
    ),
    "source_independence": frozenset(
        {"documents", "provenance_audit.verified_independent_roots"}
    ),
    "authority_style": frozenset({"documents"}),
    "popularity": frozenset({"surface_cues.popularity"}),
    "familiarity": frozenset({"surface_cues.familiarity"}),
    "precision_detail": frozenset({"documents"}),
    "user_endorsement": frozenset({"surface_cues.user_endorsement"}),
    "document_position": frozenset({"documents"}),
    "document_length": frozenset({"documents"}),
}
EXPECTED_CONTRASTS_PER_FAMILY = {
    factor: 2 if factor == "evidence_warrant" else 1 for factor in EXPECTED_VISIBLE_PATHS
}


class StimulusAudit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    protocol: str
    track: str
    item_count: int
    family_count: int
    contrast_counts: dict[str, int]
    prior_invariant: bool
    gold_leakage_detected: bool
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def _visible_differences(left: Any, right: Any, *, prefix: str = "") -> set[str]:
    if isinstance(left, dict) and isinstance(right, dict) and set(left) == set(right):
        differences: set[str] = set()
        for key in sorted(left):
            path = f"{prefix}.{key}" if prefix else str(key)
            differences.update(_visible_differences(left[key], right[key], prefix=path))
        return differences
    if left != right:
        return {prefix}
    return set()


def audit_paired_stimuli(
    trials: tuple[Trial, ...], *, track: str = "static_factorial"
) -> StimulusAudit:
    errors: list[str] = []
    families: dict[str, list[Trial]] = defaultdict(list)
    contrast_counts: Counter[str] = Counter()
    rendered_priors: set[str] = set()
    gold_leakage = False
    forbidden_keys = ('"gold_answer"', '"claim_truth"', '"actual_source"')
    for trial in trials:
        families[trial.family_id].append(trial)
        rendered_priors.add(render_prior(trial, track=track))
        posterior = render_trial(trial, track=track)
        if any(key in posterior for key in forbidden_keys):
            gold_leakage = True
            errors.append(f"{trial.item_id}:gold_or_actual_source_leakage")

    for family_id, members in sorted(families.items()):
        by_cell: dict[str, Trial] = {}
        for trial in members:
            cell_id = trial.metadata.get("design_cell_id")
            if not isinstance(cell_id, str):
                errors.append(f"{trial.item_id}:missing_design_cell_id")
                continue
            if cell_id in by_cell:
                errors.append(f"{family_id}:duplicate_design_cell_id:{cell_id}")
            by_cell[cell_id] = trial
        if "baseline" not in by_cell:
            errors.append(f"{family_id}:missing_baseline")
        for cell_id, trial in sorted(by_cell.items()):
            factor = trial.metadata.get("contrast_factor")
            control_cell = trial.metadata.get("control_cell_id")
            if cell_id == "baseline":
                if factor is not None or control_cell is not None:
                    errors.append(f"{family_id}:baseline_has_contrast_metadata")
                continue
            if not isinstance(factor, str) or factor not in EXPECTED_VISIBLE_PATHS:
                errors.append(f"{family_id}:{cell_id}:unknown_contrast_factor")
                continue
            if not isinstance(control_cell, str) or control_cell not in by_cell:
                errors.append(f"{family_id}:{cell_id}:missing_control_cell")
                continue
            control = by_cell[control_cell]
            vector_differences = {
                key
                for key in set(trial.intervention_vector) | set(control.intervention_vector)
                if trial.intervention_vector.get(key) != control.intervention_vector.get(key)
            }
            if vector_differences != {factor}:
                errors.append(
                    f"{family_id}:{cell_id}:factor_vector_diff="
                    f"{','.join(sorted(vector_differences))}"
                )
            visible_differences = _visible_differences(
                json.loads(render_trial(trial, track=track)),
                json.loads(render_trial(control, track=track)),
            )
            expected = EXPECTED_VISIBLE_PATHS[factor]
            if visible_differences != set(expected):
                errors.append(
                    f"{family_id}:{cell_id}:visible_diff="
                    f"{','.join(sorted(visible_differences))}"
                )
            contrast_counts[factor] += 1

    prior_invariant = len(rendered_priors) == len(families)
    if not prior_invariant:
        errors.append("prior_not_invariant_within_family")
    expected_counts = {
        factor: count * len(families)
        for factor, count in EXPECTED_CONTRASTS_PER_FAMILY.items()
    }
    if dict(contrast_counts) != expected_counts:
        errors.append("contrast_coverage_mismatch")
    return StimulusAudit(
        protocol="audited_static_v1",
        track=track,
        item_count=len(trials),
        family_count=len(families),
        contrast_counts=dict(sorted(contrast_counts.items())),
        prior_invariant=prior_invariant,
        gold_leakage_detected=gold_leakage,
        errors=tuple(dict.fromkeys(errors)),
    )
