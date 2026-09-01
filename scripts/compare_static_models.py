"""Publish an integrity-gated descriptive comparison of static V0 model results."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from provtrust.execution.atomic_io import atomic_write_json, sha256_file


def _load_published(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    if value.get("status") != "passed" or value.get("confirmatory") is not False:
        raise ValueError(f"input is not an accepted exploratory analysis: {path}")
    acceptance = value.get("acceptance")
    if not isinstance(acceptance, dict) or acceptance.get("failures") != []:
        raise ValueError(f"input analysis has failed integrity gates: {path}")
    results = value.get("results")
    if not isinstance(results, dict) or results.get("status") != "complete":
        raise ValueError(f"input analysis result is incomplete: {path}")
    return value


def _effect_sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def build_comparison(inputs: list[Path]) -> dict[str, Any]:
    if len(inputs) < 2:
        raise ValueError("at least two published analyses are required")
    published = [_load_published(path) for path in inputs]
    results = [value["results"] for value in published]
    models = [str(value.get("model")) for value in results]
    if len(models) != len(set(models)):
        raise ValueError("each comparison input must represent a distinct model")

    invariant_fields = (
        "dataset_sha256",
        "dataset_manifest_sha256",
        "sample_count",
        "family_count",
    )
    for field in invariant_fields:
        values = {value.get(field) for value in results}
        if len(values) != 1:
            raise ValueError(f"cross-model invariant mismatch: {field}")

    contrast_maps: list[dict[str, dict[str, Any]]] = []
    for value in results:
        rows = value.get("contrasts")
        if not isinstance(rows, list) or not rows:
            raise ValueError("published analysis has no contrast rows")
        mapping = {
            str(row["contrast_id"]): row
            for row in rows
            if isinstance(row, dict) and "contrast_id" in row
        }
        if len(mapping) != len(rows):
            raise ValueError("contrast identifiers must be unique and complete")
        contrast_maps.append(mapping)
    contrast_ids = tuple(sorted(contrast_maps[0]))
    if any(tuple(sorted(mapping)) != contrast_ids for mapping in contrast_maps[1:]):
        raise ValueError("contrast sets differ across models")

    contrast_comparison: list[dict[str, Any]] = []
    for contrast_id in contrast_ids:
        rows = [mapping[contrast_id] for mapping in contrast_maps]
        descriptors = {(row.get("factor"), row.get("factor_class")) for row in rows}
        if len(descriptors) != 1:
            raise ValueError(f"contrast metadata mismatch: {contrast_id}")
        effects = [float(row["raw_effect_mean"]) for row in rows]
        if not all(math.isfinite(value) for value in effects):
            raise ValueError(f"non-finite contrast effect: {contrast_id}")
        nonzero_signs = {_effect_sign(value) for value in effects if value != 0.0}
        contrast_comparison.append(
            {
                "contrast_id": contrast_id,
                "factor": rows[0]["factor"],
                "factor_class": rows[0]["factor_class"],
                "model_results": [
                    {
                        "model": model,
                        "raw_effect_mean": effect,
                        "ci95_lower": float(row["ci95_lower"]),
                        "ci95_upper": float(row["ci95_upper"]),
                        "randomization_p_two_sided": float(
                            row["randomization_p_two_sided"]
                        ),
                        "holm_adjusted_p": float(row["holm_adjusted_p"]),
                    }
                    for model, effect, row in zip(models, effects, rows, strict=True)
                ],
                "all_effects_exactly_equal": len(set(effects)) == 1,
                "nonzero_model_count": sum(value != 0.0 for value in effects),
                "nonzero_direction_agreement": len(nonzero_signs) <= 1,
                "effect_range": max(effects) - min(effects),
            }
        )

    model_summaries = []
    for path, value in zip(inputs, results, strict=True):
        model_summaries.append(
            {
                "model": value["model"],
                "input": path.as_posix(),
                "input_sha256": sha256_file(path),
                "git_revision": value["git_revision"],
                "plan_sha256": value["plan_sha256"],
                "accuracy": float(value["accuracy"]),
                "posterior_abstention_rate": float(value["posterior_abstention_rate"]),
                "false_verification_assurance_rate": float(
                    value["false_verification_assurance_rate"]
                ),
                "normative_factor_control_ratio": float(
                    value["normative_factor_control_ratio"]
                ),
                "holm_supported_contrast_count": sum(
                    float(row["holm_adjusted_p"]) <= 0.05
                    for row in value["contrasts"]
                ),
            }
        )

    return {
        "schema_version": "1.0.0",
        "status": "passed",
        "scope": "descriptive_cross_model_static_v0",
        "confirmatory": False,
        "scientific_claims_allowed": False,
        "shared_inputs": {
            field: results[0][field] for field in invariant_fields
        },
        "model_count": len(models),
        "models": model_summaries,
        "contrasts": contrast_comparison,
        "interpretation_boundary": (
            "This comparison describes heterogeneity across the enumerated V0 models. "
            "It performs no population-level pooling, does not convert exact-zero "
            "estimates into equivalence claims, and is not confirmatory evidence."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_comparison(args.inputs)
    digest = atomic_write_json(args.output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "model_count": report["model_count"],
                "output": args.output.as_posix(),
                "sha256": digest,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
