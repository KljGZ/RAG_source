from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

pytest.importorskip("fcntl")


def _controller() -> ModuleType:
    path = Path(__file__).parents[1] / "scripts" / "control_track_e.py"
    spec = importlib.util.spec_from_file_location("track_e_controller", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_compiled_queue_matches_frozen_v3_plans() -> None:
    controller = _controller()
    root = Path(__file__).parents[1].resolve()
    plans = [
        {"name": name, "path": path, "sha256": digest}
        for name, path, digest in controller.ALLOWED_PLAN_QUEUE
    ]

    entries = controller._plan_entries({"plans": plans}, root)

    assert (
        tuple((entry["name"], entry["path"], entry["sha256"]) for entry in entries)
        == controller.ALLOWED_PLAN_QUEUE
    )


def test_compiled_queue_rejects_reordering() -> None:
    controller = _controller()
    root = Path(__file__).parents[1].resolve()
    plans = [
        {"name": name, "path": path, "sha256": digest}
        for name, path, digest in reversed(controller.ALLOWED_PLAN_QUEUE)
    ]

    with pytest.raises(ValueError, match="compiled allowlist"):
        controller._plan_entries({"plans": plans}, root)


def test_completion_record_detects_raw_log_tampering(tmp_path: Path) -> None:
    controller = _controller()
    root = tmp_path / "repo"
    state_dir = tmp_path / "state"
    raw_log = root / "artifacts" / "runs" / "run.eval"
    raw_log.parent.mkdir(parents=True)
    raw_log.write_text("original", encoding="utf-8")
    entry = {
        "name": "interactive-v3-no-tools-preflight",
        "path": controller.ALLOWED_PLAN_QUEUE[0][1],
        "sha256": controller.ALLOWED_PLAN_QUEUE[0][2],
    }
    evidence_path = controller._evidence_path(state_dir, entry["name"])
    evidence_path.parent.mkdir(parents=True)
    raw_relative = raw_log.relative_to(root).as_posix()
    raw_hash = controller.sha256_file(raw_log)
    evidence = {
        "status": "passed",
        "plan_sha256": entry["sha256"],
        "raw_log": {"path": raw_relative, "sha256": raw_hash},
    }
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    state = {
        "status": "passed",
        "controller_id": controller.CONTROLLER_ID,
        "plan_name": entry["name"],
        "plan_path": entry["path"],
        "plan_sha256": entry["sha256"],
        "git_revision": "a" * 40,
        "exit_code": 0,
        "raw_log": raw_relative,
        "raw_log_sha256": raw_hash,
        "evidence": str(evidence_path),
        "evidence_sha256": controller.sha256_file(evidence_path),
    }
    config = {"expected_git_revision": "a" * 40}

    valid, reason = controller._completed_entry_valid(
        config, root, state_dir, entry, state, evidence
    )
    assert valid is True
    assert reason == "passed"

    raw_log.write_text("tampered", encoding="utf-8")
    valid, reason = controller._completed_entry_valid(
        config, root, state_dir, entry, state, evidence
    )
    assert valid is False
    assert reason == "completion_raw_log_hash_mismatch"
