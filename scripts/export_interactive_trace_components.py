"""Export aggregate-safe component outcomes from accepted interactive eval logs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from inspect_ai.log import read_eval_log

PREFLIGHT_ARTIFACTS = (
    "artifacts/system/INTERACTIVE_V3_NO_TOOLS_PREFLIGHT.json",
    "artifacts/system/INTERACTIVE_V3_TOOLS_UNPROMPTED_PREFLIGHT.json",
    "artifacts/system/INTERACTIVE_V3_TOOLS_PROMPTED_PREFLIGHT.json",
)


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python", exclude_none=True)
        if isinstance(dumped, dict):
            return dumped
    return {}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-directory", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root.resolve()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    sample_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    tool_rows: list[dict[str, Any]] = []

    for relative in PREFLIGHT_ARTIFACTS:
        artifact = json.loads((root / relative).read_text(encoding="utf-8"))
        policy = str(artifact["dataset"]["policy"])
        log = read_eval_log(root / artifact["raw_log"]["path"])
        component_counts: Counter[str] = Counter()
        tool_attempts: Counter[str] = Counter()
        tool_successes: Counter[str] = Counter()
        tool_failures: Counter[str] = Counter()
        samples = list(log.samples or [])

        for sample in samples:
            metadata = as_dict(sample.metadata)
            trial = as_dict(metadata.get("trial"))
            design = as_dict(trial.get("metadata"))
            score = (sample.scores or {}).get("structured_parse_scorer")
            score_metadata = as_dict(score.metadata if score is not None else None)
            verification = as_dict(score_metadata.get("verification"))
            components = as_dict(verification.get("components"))
            calls = verification.get("calls")
            call_rows = calls if isinstance(calls, list) else []
            for name, passed in components.items():
                component_counts[str(name)] += int(passed is True)
            for call in call_rows:
                call_dict = as_dict(call)
                tool_name = str(call_dict.get("tool_name", "unknown"))
                tool_attempts[tool_name] += 1
                if call_dict.get("succeeded") is True:
                    tool_successes[tool_name] += 1
                else:
                    tool_failures[tool_name] += 1

            sample_rows.append(
                {
                    "policy": policy,
                    "item_id": str(sample.id),
                    "family_id": as_dict(trial.get("claim")).get("family_id"),
                    "scenario": design.get("scenario_id"),
                    "risk": design.get("risk_condition"),
                    "triggered": verification.get("triggered"),
                    "completed": verification.get("completed"),
                    "missing_components": "|".join(
                        sorted(str(value) for value in verification.get("missing_components", []))
                    ),
                    "tool_call_count": verification.get("tool_call_count"),
                    "successful_tool_call_count": verification.get("successful_tool_call_count"),
                    "failed_tool_call_count": verification.get("failed_tool_call_count"),
                    **{f"component_{name}": passed for name, passed in sorted(components.items())},
                }
            )

        for component, passed_count in sorted(component_counts.items()):
            component_rows.append(
                {
                    "policy": policy,
                    "component": component,
                    "passed_count": passed_count,
                    "sample_count": len(samples),
                    "pass_rate": passed_count / len(samples),
                }
            )
        for tool_name in sorted(tool_attempts):
            tool_rows.append(
                {
                    "policy": policy,
                    "tool_name": tool_name,
                    "call_count": tool_attempts[tool_name],
                    "successful_call_count": tool_successes[tool_name],
                    "failed_call_count": tool_failures[tool_name],
                }
            )

    sample_rows.sort(key=lambda row: (str(row["policy"]), str(row["item_id"])))
    write_csv(args.output_directory / "interactive_preflight_trace_samples.csv", sample_rows)
    write_csv(
        args.output_directory / "interactive_preflight_verification_components.csv", component_rows
    )
    write_csv(args.output_directory / "interactive_preflight_tool_usage.csv", tool_rows)


if __name__ == "__main__":
    main()
