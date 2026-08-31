"""Verify generated V0 static analysis artifacts and publish a tracked summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from provtrust.execution.atomic_io import atomic_write_json, sha256_file


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            value = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError(f"expected JSON object at {path}:{line_number}")
            rows.append(value)
    return rows


def _portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-dir", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-model", required=True)
    parser.add_argument("--expected-plan-sha256", required=True)
    parser.add_argument("--expected-dataset-sha256", required=True)
    parser.add_argument("--expected-git-revision", required=True)
    parser.add_argument("--expected-samples", type=int, default=240)
    parser.add_argument("--expected-families", type=int, default=16)
    parser.add_argument("--expected-contrasts", type=int, default=224)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    analysis_dir = args.analysis_dir
    manifest_path = analysis_dir / "MANIFEST.json"
    manifest = _load_json(manifest_path)
    summary_ref = manifest.get("summary")
    observations_ref = manifest.get("observations")
    effects_ref = manifest.get("paired_effects")
    if not all(isinstance(value, dict) for value in (summary_ref, observations_ref, effects_ref)):
        raise TypeError("analysis manifest is missing artifact references")
    assert isinstance(summary_ref, dict)
    assert isinstance(observations_ref, dict)
    assert isinstance(effects_ref, dict)

    summary_path = analysis_dir / str(summary_ref["path"])
    observations_path = analysis_dir / str(observations_ref["path"])
    effects_path = analysis_dir / str(effects_ref["path"])
    summary = _load_json(summary_path)
    observations = _load_jsonl(observations_path)
    effects = _load_jsonl(effects_path)
    raw_logs = manifest.get("raw_logs")
    if not isinstance(raw_logs, list) or len(raw_logs) != 1 or not isinstance(raw_logs[0], dict):
        raise TypeError("analysis manifest must identify exactly one raw log")
    raw_log = raw_logs[0]
    raw_log_path = Path(str(raw_log["path"]))

    effect_keys = {
        (str(row.get("family_id")), str(row.get("model_id")), str(row.get("contrast_id")))
        for row in effects
    }
    observation_keys = {
        (
            str(row.get("family_id")),
            str(row.get("model_id")),
            str(row.get("design_cell_id")),
        )
        for row in observations
    }
    contrast_rows = summary.get("contrasts")
    if not isinstance(contrast_rows, list):
        raise TypeError("analysis summary is missing contrasts")
    contrast_ids = [str(row.get("contrast_id")) for row in contrast_rows if isinstance(row, dict)]
    contrast_family_counts = [
        int(row.get("family_count", -1)) for row in contrast_rows if isinstance(row, dict)
    ]

    gates = {
        "manifest_status_complete": manifest.get("status") == "complete",
        "manifest_hash_matches": sha256_file(manifest_path) == args.expected_manifest_sha256,
        "summary_hash_matches_manifest": sha256_file(summary_path) == summary_ref.get("sha256"),
        "observations_hash_matches_manifest": sha256_file(observations_path)
        == observations_ref.get("sha256"),
        "effects_hash_matches_manifest": sha256_file(effects_path) == effects_ref.get("sha256"),
        "raw_log_exists": raw_log_path.is_file(),
        "raw_log_hash_matches_manifest": raw_log_path.is_file()
        and sha256_file(raw_log_path) == raw_log.get("sha256"),
        "summary_status_complete": summary.get("status") == "complete",
        "exploratory_not_confirmatory": summary.get("confirmatory") is False,
        "expected_model": summary.get("model") == args.expected_model,
        "expected_plan_hash": summary.get("plan_sha256") == args.expected_plan_sha256,
        "expected_dataset_hash": summary.get("dataset_sha256") == args.expected_dataset_sha256,
        "expected_git_revision": summary.get("git_revision") == args.expected_git_revision,
        "expected_sample_count": len(observations) == args.expected_samples
        and summary.get("sample_count") == args.expected_samples
        and observations_ref.get("count") == args.expected_samples,
        "unique_observation_keys": len(observation_keys) == len(observations),
        "expected_family_count": len({key[0] for key in observation_keys}) == args.expected_families
        and summary.get("family_count") == args.expected_families,
        "expected_effect_count": len(effects) == args.expected_contrasts
        and effects_ref.get("count") == args.expected_contrasts,
        "unique_effect_keys": len(effect_keys) == len(effects),
        "fourteen_registered_contrasts": len(contrast_ids) == 14 and len(set(contrast_ids)) == 14,
        "complete_family_count_per_contrast": len(contrast_family_counts) == 14
        and all(value == args.expected_families for value in contrast_family_counts),
        "all_outputs_parsed": summary.get("parse_success_count") == args.expected_samples
        and summary.get("parse_success_rate") == 1.0,
        "all_answer_types_valid": summary.get("posterior_answer_type_valid_rate") == 1.0,
        "all_citations_valid": summary.get("citation_valid_rate") == 1.0,
        "holm_not_less_than_raw_p": all(
            isinstance(row, dict)
            and float(row["holm_adjusted_p"]) >= float(row["randomization_p_two_sided"])
            for row in contrast_rows
        ),
        "finite_effect_summaries": all(
            isinstance(row, dict)
            and all(
                isinstance(row.get(field), (int, float))
                for field in (
                    "raw_effect_mean",
                    "raw_effect_median",
                    "ci95_lower",
                    "ci95_upper",
                    "randomization_p_two_sided",
                    "holm_adjusted_p",
                )
            )
            for row in contrast_rows
        ),
    }
    failures = sorted(name for name, passed in gates.items() if not passed)
    status = "passed" if not failures else "failed"
    report = {
        "schema_version": "1.0.0",
        "status": status,
        "scope": "exploratory_single_model_closed_world_synthetic_v0",
        "confirmatory": False,
        "acceptance": {"gates": gates, "failures": failures},
        "source_analysis": {
            "directory": _portable_path(analysis_dir),
            "manifest_path": _portable_path(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "raw_log": raw_log,
            "observations": observations_ref,
            "paired_effects": effects_ref,
            "summary": summary_ref,
        },
        "results": summary,
        "interpretation_boundary": (
            "This is an integrity-checked publication of exploratory results from one "
            "open-weight model and synthetic closed-world claims. It does not establish a "
            "general or confirmatory SDI/PGSD conclusion."
        ),
    }
    output_sha256 = atomic_write_json(args.output, report)
    print(
        json.dumps(
            {
                "status": status,
                "output": args.output.as_posix(),
                "sha256": output_sha256,
                "failures": failures,
            },
            indent=2,
        )
    )
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
