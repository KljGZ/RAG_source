from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytest.importorskip("fcntl")


def _replacement_controller() -> ModuleType:
    scripts = Path(__file__).parents[1] / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        path = scripts / "control_track_e_v6_full.py"
        spec = importlib.util.spec_from_file_location("track_e_v6_full_controller", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts))


def test_replacement_queue_matches_three_fault_contained_plans() -> None:
    module = _replacement_controller()
    root = Path(__file__).parents[1].resolve()
    plans = [
        {"name": name, "path": path, "sha256": digest}
        for name, path, digest in module.controller.ALLOWED_PLAN_QUEUE
    ]

    entries = module.controller._plan_entries({"plans": plans}, root)

    assert [entry["name"] for entry in entries] == [
        "interactive-v5-no-tools-full",
        "interactive-v5-tools-unprompted-full",
        "interactive-v5-tools-prompted-full",
    ]


def test_replacement_queue_rejects_reordering() -> None:
    module = _replacement_controller()
    root = Path(__file__).parents[1].resolve()
    plans = [
        {"name": name, "path": path, "sha256": digest}
        for name, path, digest in reversed(module.controller.ALLOWED_PLAN_QUEUE)
    ]

    with pytest.raises(ValueError, match="compiled allowlist"):
        module.controller._plan_entries({"plans": plans}, root)
