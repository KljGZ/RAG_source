from __future__ import annotations

from pathlib import Path

from scripts.validate_interactive_environment import validate_environment


def test_frozen_interactive_environment_passes_model_free_semantic_acceptance() -> None:
    report = validate_environment(
        root=Path.cwd(),
        dataset_manifest_path=Path(
            "benchmark/manifests/v0-interactive-v1-tools_prompted.yaml"
        ),
        tool_manifest_path=Path("benchmark/manifests/interactive-v1-tools.yaml"),
        expected_policy="tools_prompted",
    )

    assert report["status"] == "passed"
    assert report["model_calls"] == 0
    assert report["tool_environment"]["document_count"] == 81
    assert report["tool_environment"]["snapshot_count"] == 81
    assert report["tool_environment"]["trial_semantic_checks"] == 1120
