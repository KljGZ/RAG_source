"""Export the audit-safe V0 evidence tables tracked for public review.

The source observation and paired-effect tables are content-addressed analysis
outputs that remain outside Git.  This exporter copies only structured scientific
fields: it never copies prompts, model message text, tool payloads, or raw eval logs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "data" / "v0_to_current"

STATIC_RUNS = (
    {
        "label": "qwen3_14b_parser_v3",
        "acceptance": ROOT / "artifacts/system/V0_QWEN3_14B_V3_RUN_ACCEPTANCE.json",
        "analysis": ROOT / "artifacts/system/V0_QWEN3_14B_V3_ANALYSIS.json",
        "observations": ROOT / "artifacts/analyses/v0_qwen3_14b_paired_v3/observations.jsonl",
        "paired_effects": ROOT / "artifacts/analyses/v0_qwen3_14b_paired_v3/paired_effects.jsonl",
    },
    {
        "label": "phi4_parser_v3",
        "acceptance": ROOT / "artifacts/system/V0_PHI4_V3_RUN_ACCEPTANCE.json",
        "analysis": ROOT / "artifacts/system/V0_PHI4_V3_ANALYSIS.json",
        "observations": ROOT / "artifacts/analyses/v0_phi4_paired_v3/observations.jsonl",
        "paired_effects": ROOT / "artifacts/analyses/v0_phi4_paired_v3/paired_effects.jsonl",
    },
)

INTERACTIVE_PREFLIGHTS = (
    ROOT / "artifacts/system/INTERACTIVE_V3_NO_TOOLS_PREFLIGHT.json",
    ROOT / "artifacts/system/INTERACTIVE_V3_TOOLS_UNPROMPTED_PREFLIGHT.json",
    ROOT / "artifacts/system/INTERACTIVE_V3_TOOLS_PROMPTED_PREFLIGHT.json",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str] | None = None) -> None:
    materialized = list(rows)
    if not materialized and fields is None:
        raise ValueError(f"cannot infer columns for empty table: {path}")
    if fields is None:
        fields = sorted({key for row in materialized for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in materialized:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})


def flatten_factors(row: dict[str, Any]) -> dict[str, Any]:
    flat = {key: value for key, value in row.items() if key != "factors"}
    for key, value in sorted(row.get("factors", {}).items()):
        flat[f"factor_{key}"] = value
    return flat


def mean(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [float(row[field]) for row in rows if row.get(field) is not None]
    return sum(values) / len(values) if values else None


def rate(count: int, denominator: int) -> float | None:
    return count / denominator if denominator else None


def export_static() -> list[Path]:
    model_rows: list[dict[str, Any]] = []
    contrast_rows: list[dict[str, Any]] = []
    observation_rows: list[dict[str, Any]] = []
    effect_rows: list[dict[str, Any]] = []

    for source in STATIC_RUNS:
        acceptance = read_json(source["acceptance"])
        result = read_json(source["analysis"])["results"]
        observations = read_jsonl(source["observations"])
        effects = read_jsonl(source["paired_effects"])
        counts = acceptance["observations"]
        tokens = counts["aggregate_tokens"]
        raw_log = acceptance["raw_log"]
        sample_count = int(result["sample_count"])

        model_rows.append(
            {
                "run_label": source["label"],
                "model": result["model"],
                "git_revision": result["git_revision"],
                "model_root_sha256": acceptance["model_asset"]["root_sha256"],
                "plan_sha256": result["plan_sha256"],
                "dataset_sha256": result["dataset_sha256"],
                "raw_eval_sha256": raw_log["sha256"],
                "sample_count": sample_count,
                "family_count": result["family_count"],
                "model_call_count": counts["model_call_count"],
                "sample_error_count": counts["sample_error_count"],
                "error_retry_count": counts["error_retry_count"],
                "parse_success_count": counts["parse_success_count"],
                "parse_success_rate": result["parse_success_rate"],
                "correct_count": counts["correct_count"],
                "accuracy": result["accuracy"],
                "posterior_abstained_count": counts["posterior_abstained_count"],
                "posterior_abstention_rate": result["posterior_abstention_rate"],
                "claimed_verified_count": counts["claimed_verified_count"],
                "claimed_verified_rate": rate(counts["claimed_verified_count"], sample_count),
                "verification_completed_count": counts["verification_completed_count"],
                "verification_completed_rate": rate(
                    counts["verification_completed_count"], sample_count
                ),
                "false_verification_assurance_count": counts["false_verification_assurance_count"],
                "false_verification_assurance_rate": result["false_verification_assurance_rate"],
                "citation_valid_rate": result["citation_valid_rate"],
                "posterior_answer_type_valid_rate": result["posterior_answer_type_valid_rate"],
                "input_tokens": tokens["input"],
                "output_tokens": tokens["output"],
                "total_tokens": result["total_tokens"],
                "summed_sample_seconds": result["total_sample_seconds"],
                "wall_time_seconds": raw_log["wall_time_seconds"],
                "confirmatory": result["confirmatory"],
                "scope": result["scope"],
            }
        )

        for contrast in result["contrasts"]:
            contrast_rows.append(
                {
                    "run_label": source["label"],
                    "model": result["model"],
                    **contrast,
                    "holm_supported_at_0_05": contrast["holm_adjusted_p"] <= 0.05,
                }
            )

        for observation in observations:
            observation_rows.append({"run_label": source["label"], **flatten_factors(observation)})
        for effect in effects:
            effect_rows.append({"run_label": source["label"], **effect})

    observation_rows.sort(
        key=lambda row: (row["run_label"], row["family_id"], row["design_cell_id"], row["item_id"])
    )
    effect_rows.sort(key=lambda row: (row["run_label"], row["contrast_id"], row["family_id"]))
    contrast_rows.sort(key=lambda row: (row["run_label"], row["contrast_id"]))

    cell_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in observation_rows:
        cell_groups[(row["run_label"], row["model_id"], row["design_cell_id"])].append(row)
    cell_rows = []
    for (run_label, model, cell), rows in sorted(cell_groups.items()):
        cell_rows.append(
            {
                "run_label": run_label,
                "model": model,
                "design_cell_id": cell,
                "n": len(rows),
                "claim_adoption_shift_mean": mean(rows, "claim_adoption_shift"),
                "accuracy": mean(rows, "correct"),
                "posterior_confidence_mean": mean(rows, "posterior_confidence"),
                "posterior_abstention_rate": mean(rows, "posterior_abstained"),
                "claimed_verified_rate": mean(rows, "claimed_verified"),
                "verification_completed_rate": mean(rows, "verification_completed"),
                "false_verification_assurance_rate": mean(rows, "false_verification_assurance"),
                "total_tokens": sum(int(row["total_tokens"]) for row in rows),
                "summed_sample_seconds": sum(float(row["total_time_seconds"]) for row in rows),
            }
        )

    outputs = [
        OUTPUT / "static_model_summary.csv",
        OUTPUT / "static_contrasts.csv",
        OUTPUT / "static_samples.csv",
        OUTPUT / "static_paired_effects.csv",
        OUTPUT / "static_design_cell_summary.csv",
    ]
    write_csv(outputs[0], model_rows)
    write_csv(outputs[1], contrast_rows)
    write_csv(outputs[2], observation_rows)
    write_csv(outputs[3], effect_rows)
    write_csv(outputs[4], cell_rows)
    return outputs


def export_interactive_preflights() -> list[Path]:
    summary_rows: list[dict[str, Any]] = []
    sample_rows: list[dict[str, Any]] = []
    for path in INTERACTIVE_PREFLIGHTS:
        artifact = read_json(path)
        counts = artifact["observations"]
        tokens = counts["aggregate_tokens"]
        sample_count = int(counts["sample_count"])
        triggered = int(counts["triggered_count"])
        policy = artifact["dataset"]["policy"]
        summary_rows.append(
            {
                "policy": policy,
                "artifact": path.relative_to(ROOT).as_posix(),
                "status": artifact["status"],
                "scientific_claims_allowed": artifact["scientific_claims_allowed"],
                "git_revision": artifact["model"]["revision"],
                "model": artifact["model"]["inspect_id"],
                "plan_sha256": artifact["plan_sha256"],
                "dataset_sha256": artifact["dataset"]["sha256"],
                "raw_eval_sha256": artifact["raw_log"]["sha256"],
                "sample_count": sample_count,
                "family_count": counts["family_count"],
                "model_turn_count": counts["model_turn_count"],
                "sample_error_count": counts["sample_error_count"],
                "error_retry_count": counts["error_retry_count"],
                "parse_success_count": counts["parse_success_count"],
                "triggered_count": triggered,
                "trigger_rate": rate(triggered, sample_count),
                "completed_count": counts["completed_count"],
                "completion_rate": rate(counts["completed_count"], sample_count),
                "completion_given_trigger_rate": rate(counts["completed_count"], triggered),
                "correct_count": counts["correct_count"],
                "accuracy": rate(counts["correct_count"], sample_count),
                "abstained_count": counts["abstained_count"],
                "abstention_rate": rate(counts["abstained_count"], sample_count),
                "claimed_verified_count": counts["claimed_verified_count"],
                "claimed_verified_rate": rate(counts["claimed_verified_count"], sample_count),
                "false_verification_assurance_count": counts["false_verification_assurance_count"],
                "false_verification_assurance_rate": rate(
                    counts["false_verification_assurance_count"], sample_count
                ),
                "tool_call_count": counts["tool_call_count"],
                "failed_tool_call_count": counts["failed_tool_call_count"],
                "input_tokens": tokens["input"],
                "output_tokens": tokens["output"],
                "total_tokens": tokens["total"],
                "summed_sample_seconds": counts["summed_sample_seconds"],
                "wall_time_seconds": artifact["raw_log"]["wall_time_seconds"],
            }
        )
        for sample in artifact["samples"]:
            sample_rows.append({"artifact": path.name, **sample})

    summary_rows.sort(key=lambda row: row["policy"])
    sample_rows.sort(key=lambda row: (row["policy"], row["scenario"], row["risk"]))
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in sample_rows:
        groups[(row["policy"], row["scenario"], row["risk"])].append(row)
    cell_rows = []
    for (policy, scenario, risk_level), rows in sorted(groups.items()):
        cell_rows.append(
            {
                "policy": policy,
                "scenario": scenario,
                "risk": risk_level,
                "n": len(rows),
                "trigger_rate": mean(rows, "triggered"),
                "completion_rate": mean(rows, "completed"),
                "accuracy": mean(rows, "correct"),
                "claim_adoption_shift_mean": mean(rows, "claim_adoption_shift"),
                "posterior_confidence_mean": mean(rows, "posterior_confidence"),
                "abstention_rate": mean(rows, "abstained"),
                "claimed_verified_rate": mean(rows, "claimed_verified"),
                "false_verification_assurance_rate": mean(rows, "false_verification_assurance"),
                "tool_call_count": sum(int(row["tool_call_count"]) for row in rows),
                "failed_tool_call_count": sum(int(row["failed_tool_call_count"]) for row in rows),
                "total_tokens": sum(int(row["total_tokens"]) for row in rows),
            }
        )

    outputs = [
        OUTPUT / "interactive_preflight_summary.csv",
        OUTPUT / "interactive_preflight_samples.csv",
        OUTPUT / "interactive_preflight_cell_summary.csv",
    ]
    write_csv(outputs[0], summary_rows)
    write_csv(outputs[1], sample_rows)
    write_csv(outputs[2], cell_rows)
    return outputs


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    selected = []
    prefixes = ("analysis/preregistration/", "artifacts/system/", "benchmark/", "reports/")
    for relative in result.stdout.splitlines():
        normalized = relative.replace("\\", "/")
        if normalized.startswith(prefixes) and not normalized.startswith(
            "reports/data/v0_to_current/"
        ):
            selected.append(ROOT / relative)
    return sorted(selected)


def export_manifests(generated: list[Path]) -> list[Path]:
    evidence_rows = []
    for path in tracked_files():
        evidence_rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "git_tracked": True,
            }
        )
    evidence_path = OUTPUT / "tracked_evidence_manifest.csv"
    write_csv(evidence_path, evidence_rows)

    raw_rows = []
    for path in sorted((ROOT / "artifacts/system").glob("*.json")):
        artifact = read_json(path)
        raw = artifact.get("raw_log")
        if not isinstance(raw, dict) or not raw.get("sha256"):
            continue
        raw_rows.append(
            {
                "evidence_artifact": path.relative_to(ROOT).as_posix(),
                "artifact_status": artifact.get("status", ""),
                "run_kind": artifact.get("run_kind", ""),
                "raw_log_path_on_research_hosts": raw.get("path", ""),
                "raw_log_bytes": raw.get("bytes", ""),
                "raw_log_sha256": raw["sha256"],
                "git_uploaded": False,
                "retention": "compute_and_workstation_content_addressed_storage",
                "exclusion_reason": "contains_unrestricted_model_or_tool_trace",
            }
        )
    raw_path = OUTPUT / "raw_eval_hash_manifest.csv"
    write_csv(raw_path, raw_rows)

    trace_exports = [
        OUTPUT / "interactive_preflight_trace_samples.csv",
        OUTPUT / "interactive_preflight_verification_components.csv",
        OUTPUT / "interactive_preflight_tool_usage.csv",
    ]
    checksummed = sorted(
        [*generated, evidence_path, raw_path, *(path for path in trace_exports if path.is_file())],
        key=lambda path: path.name,
    )
    sums_path = OUTPUT / "SHA256SUMS"
    sums_path.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in checksummed),
        encoding="utf-8",
        newline="\n",
    )
    return [evidence_path, raw_path, sums_path]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    generated = [*export_static(), *export_interactive_preflights()]
    generated.extend(export_manifests(generated))
    print(f"exported {len(generated)} audit-safe files to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
