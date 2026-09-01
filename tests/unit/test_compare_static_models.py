from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.compare_static_models import build_comparison


def _published(path: Path, *, model: str, dataset: str = "d" * 64) -> Path:
    contrast = {
        "contrast_id": "identity_false",
        "factor": "identity_authenticity",
        "factor_class": "normative",
        "raw_effect_mean": -0.25 if model == "model-a" else 0.0,
        "ci95_lower": -0.5,
        "ci95_upper": 0.0,
        "randomization_p_two_sided": 0.25,
        "holm_adjusted_p": 1.0,
    }
    value = {
        "status": "passed",
        "confirmatory": False,
        "acceptance": {"failures": []},
        "results": {
            "status": "complete",
            "model": model,
            "dataset_sha256": dataset,
            "dataset_manifest_sha256": "m" * 64,
            "sample_count": 240,
            "family_count": 16,
            "git_revision": "abc1234",
            "plan_sha256": "p" * 64,
            "accuracy": 0.5,
            "posterior_abstention_rate": 0.0,
            "false_verification_assurance_rate": 0.8,
            "normative_factor_control_ratio": 1.0,
            "contrasts": [contrast],
        },
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_build_comparison_preserves_model_level_results(tmp_path: Path) -> None:
    result = build_comparison(
        [
            _published(tmp_path / "a.json", model="model-a"),
            _published(tmp_path / "b.json", model="model-b"),
        ]
    )
    assert result["status"] == "passed"
    assert result["model_count"] == 2
    assert result["contrasts"][0]["nonzero_model_count"] == 1
    assert result["contrasts"][0]["nonzero_direction_agreement"] is True
    assert result["contrasts"][0]["all_effects_exactly_equal"] is False


def test_build_comparison_rejects_dataset_mismatch(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="dataset_sha256"):
        build_comparison(
            [
                _published(tmp_path / "a.json", model="model-a"),
                _published(tmp_path / "b.json", model="model-b", dataset="e" * 64),
            ]
        )
