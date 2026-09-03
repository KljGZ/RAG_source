"""Combine three accepted Track E policy runs under the frozen V0 analysis plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from provtrust.analysis.interactive_results import (
    InteractiveObservation,
    holm_adjust,
    paired_contrast,
)
from provtrust.execution.atomic_io import atomic_write_json, sha256_file

POLICIES = {"no_tools", "tools_unprompted", "tools_prompted"}
POLICY_OUTCOMES = (
    "triggered",
    "completed",
    "tool_call_count",
    "false_verification_assurance",
    "posterior_abstained",
    "posterior_confidence",
    "confidence_change",
    "correct",
    "claim_adoption_shift",
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object:{path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            value = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError(f"expected JSON object:{path}:{line_number}")
            rows.append(value)
    return rows


def _resolve_project_path(value: Any) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("analysis path must be project-relative")
    root = Path.cwd().resolve()
    path = (root / value).resolve()
    if path == root or root not in path.parents:
        raise ValueError("analysis path escapes project root")
    return path


def _accepted_observations(
    evidence_path: Path,
) -> tuple[dict[str, Any], list[InteractiveObservation]]:
    evidence = _load_json(evidence_path)
    if (
        evidence.get("status") != "passed"
        or evidence.get("confirmatory") is not False
        or evidence.get("run_kind") != "exploratory_v0_full"
    ):
        raise ValueError(f"input is not an accepted exploratory full run:{evidence_path}")
    acceptance = evidence.get("acceptance")
    if not isinstance(acceptance, dict) or acceptance.get("failures") != []:
        raise ValueError(f"input contains failed integrity gates:{evidence_path}")
    analysis = evidence.get("analysis")
    if not isinstance(analysis, dict):
        raise TypeError(f"input lacks analysis identity:{evidence_path}")
    analysis_dir = _resolve_project_path(analysis.get("directory"))
    manifest_path = analysis_dir / "MANIFEST.json"
    manifest = _load_json(manifest_path)
    if sha256_file(manifest_path) != analysis.get("manifest_sha256"):
        raise ValueError(f"analysis manifest hash mismatch:{evidence_path}")
    observations_ref = manifest.get("observations")
    if not isinstance(observations_ref, dict):
        raise TypeError(f"analysis manifest lacks observations:{evidence_path}")
    observations_path = analysis_dir / str(observations_ref.get("path"))
    if sha256_file(observations_path) != observations_ref.get("sha256"):
        raise ValueError(f"observation hash mismatch:{evidence_path}")
    rows = _load_jsonl(observations_path)
    observations = [InteractiveObservation.model_validate(row) for row in rows]
    if len(observations) != observations_ref.get("count"):
        raise ValueError(f"observation count mismatch:{evidence_path}")
    return evidence, observations


def _contrast_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapping = {
        str(row["contrast_id"]): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("contrast_id"), str)
    }
    if len(mapping) != len(rows):
        raise ValueError("contrast identifiers are missing or duplicated")
    return mapping


def _policy_contrasts(
    observations: list[InteractiveObservation], *, seed: int
) -> list[dict[str, Any]]:
    pairs = (
        ("tools_unprompted_minus_no_tools", "no_tools", "tools_unprompted"),
        ("tools_prompted_minus_tools_unprompted", "tools_unprompted", "tools_prompted"),
    )
    rows: list[dict[str, Any]] = []
    for pair_index, (prefix, left, right) in enumerate(pairs):
        for outcome_index, outcome in enumerate(POLICY_OUTCOMES):
            rows.append(
                paired_contrast(
                    observations,
                    contrast_id=f"{prefix}:{outcome}",
                    outcome=outcome,
                    level_field="policy",
                    left_level=left,
                    right_level=right,
                    pair_key_fields=("family_id", "scenario", "risk"),
                    seed=seed + pair_index * len(POLICY_OUTCOMES) + outcome_index,
                )
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs=3, type=Path)
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    loaded = [_accepted_observations(path) for path in args.inputs]
    evidences = [value[0] for value in loaded]
    by_policy: dict[str, tuple[dict[str, Any], list[InteractiveObservation]]] = {}
    for evidence, observations in loaded:
        results = evidence.get("results")
        if not isinstance(results, dict):
            raise TypeError("accepted evidence lacks results")
        policy = str(results.get("policy"))
        if policy in by_policy:
            raise ValueError(f"duplicate policy input:{policy}")
        by_policy[policy] = (evidence, observations)
    if set(by_policy) != POLICIES:
        raise ValueError("inputs do not cover the exact three-policy matrix")

    models = {str(value[0].get("results", {}).get("model")) for value in by_policy.values()}
    revisions = {
        str(value[0].get("results", {}).get("git_revision")) for value in by_policy.values()
    }
    if len(models) != 1 or len(revisions) != 1:
        raise ValueError("policy runs differ in model or Git revision")

    observations = [row for _, rows in by_policy.values() for row in rows]
    if len(observations) != 480:
        raise ValueError("combined matrix does not contain exactly 480 observations")
    matched_keys: dict[str, set[tuple[str, str, str]]] = {}
    for policy, (_, rows) in by_policy.items():
        keys = {(row.family_id, row.scenario, row.risk) for row in rows}
        if len(keys) != 160:
            raise ValueError(f"policy contains duplicate matched cells:{policy}")
        matched_keys[policy] = keys
    if len({frozenset(value) for value in matched_keys.values()}) != 1:
        raise ValueError("policy datasets do not share exact matched cells")

    policy_contrasts = _policy_contrasts(observations, seed=args.seed)
    policy_map = _contrast_map(policy_contrasts)
    risk_maps = {
        policy: _contrast_map(list(value[0]["results"].get("risk_contrasts", [])))
        for policy, value in by_policy.items()
    }
    primary_specs = (
        (
            "h5a_unprompted_risk_trigger",
            risk_maps["tools_unprompted"]["risk_high_minus_low:triggered"],
            1,
        ),
        (
            "h5b_unprompted_risk_completion",
            risk_maps["tools_unprompted"]["risk_high_minus_low:completed"],
            1,
        ),
        (
            "h5c_prompted_completion",
            policy_map["tools_prompted_minus_tools_unprompted:completed"],
            1,
        ),
        (
            "h5e_unresolved_risk_abstention",
            risk_maps["tools_unprompted"][
                "risk_high_minus_low:both_unresolved:posterior_abstained"
            ],
            1,
        ),
        (
            "h5e_unresolved_risk_confidence",
            risk_maps["tools_unprompted"][
                "risk_high_minus_low:both_unresolved:posterior_confidence"
            ],
            -1,
        ),
    )
    raw_p: dict[str, float] = {}
    for hypothesis, row, _ in primary_specs:
        p_value = row.get("cluster_sign_flip_p_two_sided")
        if isinstance(p_value, (int, float)):
            raw_p[hypothesis] = float(p_value)
    adjusted = holm_adjust(raw_p)
    primary_results: list[dict[str, Any]] = []
    for hypothesis, row, expected_sign in primary_specs:
        estimate = row.get("estimate")
        p_value = row.get("cluster_sign_flip_p_two_sided")
        direction_matches = isinstance(estimate, (int, float)) and (
            (expected_sign > 0 and float(estimate) > 0.0)
            or (expected_sign < 0 and float(estimate) < 0.0)
        )
        primary_results.append(
            {
                "hypothesis": hypothesis,
                "expected_direction": "positive" if expected_sign > 0 else "negative",
                "contrast_id": row.get("contrast_id"),
                "estimate": estimate,
                "ci95_lower": row.get("ci95_lower"),
                "ci95_upper": row.get("ci95_upper"),
                "raw_p_two_sided": p_value,
                "holm_adjusted_p": adjusted.get(hypothesis),
                "direction_matches": direction_matches,
                "exploratory_holm_supported": direction_matches
                and adjusted.get(hypothesis, 1.0) <= 0.05,
                "matched_pair_count": row.get("matched_pair_count"),
                "family_cluster_count": row.get("family_cluster_count"),
            }
        )

    report = {
        "schema_version": "1.0.0",
        "status": "passed",
        "scope": "three_policy_single_model_closed_world_interactive_v0",
        "confirmatory": False,
        "scientific_claims_allowed": True,
        "model": next(iter(models)),
        "git_revision": next(iter(revisions)),
        "sample_count": len(observations),
        "family_count": len({value.family_id for value in observations}),
        "policies": {
            policy: {
                "evidence_path": args.inputs[
                    next(index for index, evidence in enumerate(evidences) if evidence is value[0])
                ].as_posix(),
                "evidence_sha256": sha256_file(
                    args.inputs[
                        next(
                            index
                            for index, evidence in enumerate(evidences)
                            if evidence is value[0]
                        )
                    ]
                ),
                "plan_sha256": value[0].get("plan_sha256"),
                "rates": value[0]["results"].get("rates"),
                "rates_by_risk": value[0]["results"].get("rates_by_risk"),
                "rates_by_scenario": value[0]["results"].get("rates_by_scenario"),
                "risk_contrasts": value[0]["results"].get("risk_contrasts"),
            }
            for policy, value in sorted(by_policy.items())
        },
        "policy_contrasts": policy_contrasts,
        "primary_exploratory_family": {
            "multiplicity_method": "Holm across five frozen H5a/H5b/H5c/H5e tests",
            "results": primary_results,
        },
        "h5d_false_assurance": {
            policy: value[0]["results"]["rates"]["false_verification_assurance"]
            for policy, value in sorted(by_policy.items())
        },
        "interpretation_boundary": (
            "These estimates describe one model snapshot in a synthetic closed world. "
            "Holm-supported is an exploratory label, not confirmatory evidence. "
            "C1-C5 differences remain diagnostic profiles; unresolved-only H5e analyses "
            "condition on a post-treatment state and are not causal effects."
        ),
    }
    output_hash = atomic_write_json(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": args.output.as_posix(),
                "sha256": output_hash,
                "samples": report["sample_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
