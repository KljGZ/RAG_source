"""One-shot, allowlisted Track E queue controller for hourly scheduling."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil
import yaml

from provtrust.execution.atomic_io import append_jsonl, atomic_write_json, sha256_file
from provtrust.execution.input_gate import validate_frozen_execution_inputs

CONTROLLER_ID = "track-e-v3-preflight-queue"
CONTROLLER_CONFIG = "configs/controller/track_e_v3.local.yaml"
CONTROLLER_SCRIPT = "scripts/control_track_e.py"
MONITOR_CONFIG = "configs/monitoring/remote.local.yaml"
ALLOCATION_CONFIG = "configs/clusters/allocation.local.yaml"
STATE_DIRECTORY_NAME = "track-e-v3"
PHYSICAL_GPU_INDEX = 2
MINIMUM_FREE_GPU_MEMORY_GIB = 45.0
MINIMUM_STABLE_READINGS = 2
MINIMUM_STABLE_INTERVAL_SECONDS = 5.0
ALLOWED_PLAN_QUEUE = (
    (
        "interactive-v3-no-tools-preflight",
        "configs/experiments/pilot_qwen3_14b_interactive_v3_no_tools_preflight.yaml",
        "e97104928946c0cdce150c2b59502f3f8d45346712db9a5a8e1fcfbecfc18070",
    ),
    (
        "interactive-v3-tools-unprompted-preflight",
        "configs/experiments/pilot_qwen3_14b_interactive_v3_tools_unprompted_preflight.yaml",
        "26431de3b59344d15f835a2586374c5d7be2bd57f73caeb32c7985073593bb56",
    ),
    (
        "interactive-v3-tools-prompted-preflight",
        "configs/experiments/pilot_qwen3_14b_interactive_v3_tools_prompted_preflight.yaml",
        "668f6229bcca60a642201028c2a5c57bf455e7977137b75cbdd4a4542a351f74",
    ),
)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def _project_file(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty project-relative path")
    relative = Path(value)
    if relative.is_absolute():
        raise ValueError(f"{label} must be project-relative")
    resolved = (root / relative).resolve()
    if resolved == root or root not in resolved.parents or not resolved.is_file():
        raise ValueError(f"{label} is missing or escapes the project root")
    return resolved


def _external_directory(value: Any, allowed_root: Path, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty absolute path")
    path = Path(value).resolve()
    allowed_root = allowed_root.resolve()
    if not path.is_absolute() or path == allowed_root or allowed_root not in path.parents:
        raise ValueError(f"{label} must be a child of the configured state root")
    return path


def _load_config(path: Path) -> tuple[dict[str, Any], Path, Path]:
    path = path.resolve()
    config = _object(yaml.safe_load(path.read_text(encoding="utf-8")), "controller config")
    root = Path(str(config.get("project_root", ""))).resolve()
    if not root.is_dir():
        raise ValueError("project_root is not a directory")
    if path != (root / CONTROLLER_CONFIG).resolve():
        raise ValueError("only the deployment-local controller config is allowed")
    if root.name != "RAG_source" or root.parent.name != "projects":
        raise ValueError("project_root does not match the deployed repository layout")
    user_home = root.parent.parent.resolve()
    allowed_state_root = Path(str(config.get("allowed_state_root", ""))).resolve()
    expected_state_root = (user_home / "provtrust_runs").resolve()
    if allowed_state_root != expected_state_root:
        raise ValueError("allowed_state_root differs from the deployment profile")
    state_dir = _external_directory(config.get("state_dir"), allowed_state_root, "state_dir")
    if state_dir != (expected_state_root / STATE_DIRECTORY_NAME).resolve():
        raise ValueError("state_dir differs from the deployment profile")
    if config.get("schema_version") != "1.0.0" or config.get("controller_id") != CONTROLLER_ID:
        raise ValueError("controller identity differs from the deployment profile")
    if config.get("controller_script") != CONTROLLER_SCRIPT:
        raise ValueError("controller_script differs from the deployment profile")
    if config.get("monitor_config") != MONITOR_CONFIG:
        raise ValueError("monitor_config differs from the deployment profile")
    if config.get("allocation") != ALLOCATION_CONFIG:
        raise ValueError("allocation differs from the deployment profile")
    if int(config.get("physical_gpu_index", -1)) != PHYSICAL_GPU_INDEX:
        raise ValueError("only physical GPU 2 is authorized")
    if float(config.get("minimum_free_gpu_memory_gib", 0)) < MINIMUM_FREE_GPU_MEMORY_GIB:
        raise ValueError("GPU free-memory threshold weakens the deployment policy")
    if int(config.get("stable_readings", 0)) < MINIMUM_STABLE_READINGS:
        raise ValueError("stable GPU reading count weakens the deployment policy")
    if float(config.get("stable_interval_seconds", 0)) < MINIMUM_STABLE_INTERVAL_SECONDS:
        raise ValueError("stable GPU reading interval weakens the deployment policy")
    expected_python = (user_home / "miniforge3/envs/provtrust/bin/python").resolve()
    configured_python = Path(str(config.get("python_executable", ""))).resolve()
    if configured_python != expected_python or configured_python != Path(sys.executable).resolve():
        raise ValueError("controller is not running under the frozen provtrust environment")
    expected_provtrust = (expected_python.parent / "provtrust").resolve()
    if Path(str(config.get("provtrust_executable", ""))).resolve() != expected_provtrust:
        raise ValueError("provtrust_executable differs from the frozen environment")
    allowed_state_root.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    allowed_state_root.chmod(0o700)
    state_dir.chmod(0o700)
    return config, root, state_dir


def _git_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _verify_controller_identity(config: dict[str, Any], root: Path) -> Path:
    controller = _project_file(root, config.get("controller_script"), "controller_script")
    controller_hash = config.get("controller_sha256")
    if not isinstance(controller_hash, str) or len(controller_hash) != 64:
        raise RuntimeError("controller script hash is not a SHA-256 digest")
    if sha256_file(controller) != controller_hash:
        raise RuntimeError("controller script hash mismatch")
    revision = config.get("expected_git_revision")
    if not isinstance(revision, str) or len(revision) != 40:
        raise RuntimeError("expected Git revision is not a full commit hash")
    if _git_revision(root) != revision:
        raise RuntimeError("Git revision differs from the frozen controller revision")
    return controller


def _run_monitor(config: dict[str, Any], root: Path) -> dict[str, Any]:
    executable = Path(str(config.get("provtrust_executable", ""))).resolve()
    if not executable.is_file():
        raise ValueError("provtrust_executable is missing")
    monitor_config = _project_file(root, config.get("monitor_config"), "monitor_config")
    result = subprocess.run(
        [str(executable), "monitor", "--config", str(monitor_config), "--once"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        report = _object(json.loads(result.stdout), "monitor report")
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("monitor did not return a JSON report") from error
    report["exit_code"] = result.returncode
    return report


def _gpu_free_mib(index: int) -> int:
    result = subprocess.run(
        [
            "nvidia-smi",
            f"--id={index}",
            "--query-gpu=memory.free",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError("nvidia-smi did not return exactly one GPU row")
    return int(lines[0])


def _stable_gpu_readings(config: dict[str, Any]) -> list[int]:
    count = int(config.get("stable_readings", 2))
    interval = float(config.get("stable_interval_seconds", 5.0))
    if count < 2 or count > 5 or interval < 1.0 or interval > 30.0:
        raise ValueError("invalid stable GPU reading policy")
    index = int(config.get("physical_gpu_index", -1))
    if index < 0:
        raise ValueError("physical_gpu_index must be non-negative")
    readings: list[int] = []
    for position in range(count):
        readings.append(_gpu_free_mib(index))
        if position + 1 < count:
            time.sleep(interval)
    return readings


def _plan_log_directory(root: Path, plan: dict[str, Any]) -> Path:
    command = plan.get("inspect_command")
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        raise ValueError("plan inspect_command is invalid")
    indices = [index for index, part in enumerate(command) if part == "--log-dir"]
    if len(indices) != 1 or indices[0] + 1 >= len(command):
        raise ValueError("plan must declare exactly one log directory")
    relative = Path(command[indices[0] + 1])
    resolved = (root / relative).resolve()
    if relative.is_absolute() or resolved == root or root not in resolved.parents:
        raise ValueError("plan log directory escapes project root")
    return resolved


def _plan_entries(config: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    values = config.get("plans")
    if not isinstance(values, list) or not values:
        raise ValueError("controller requires a non-empty plan queue")
    supplied_queue: list[tuple[Any, Any, Any]] = []
    for value in values:
        entry = _object(value, "plan entry")
        supplied_queue.append((entry.get("name"), entry.get("path"), entry.get("sha256")))
    if tuple(supplied_queue) != ALLOWED_PLAN_QUEUE:
        raise ValueError("plan queue differs from the controller's compiled allowlist")
    entries: list[dict[str, Any]] = []
    names: set[str] = set()
    for value in values:
        entry = _object(value, "plan entry")
        name = entry.get("name")
        expected_hash = entry.get("sha256")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("plan names must be non-empty and unique")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise ValueError(f"plan hash is invalid: {name}")
        path = _project_file(root, entry.get("path"), f"plan:{name}")
        if sha256_file(path) != expected_hash:
            raise ValueError(f"plan hash mismatch: {name}")
        names.add(name)
        entries.append({**entry, "resolved_path": path})
    return entries


def _state_path(state_dir: Path, name: str) -> Path:
    return state_dir / "plans" / f"{name}.json"


def _evidence_path(state_dir: Path, name: str) -> Path:
    return state_dir / "evidence" / f"{name}.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return _object(json.loads(path.read_text(encoding="utf-8")), str(path))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _completed_entry_valid(
    config: dict[str, Any],
    root: Path,
    state_dir: Path,
    entry: dict[str, Any],
    state: dict[str, Any] | None,
    evidence: dict[str, Any] | None,
) -> tuple[bool, str]:
    name = str(entry["name"])
    evidence_path = _evidence_path(state_dir, name).resolve()
    if state is None or evidence is None:
        return False, "completion_record_unreadable"
    expected_state = {
        "status": "passed",
        "controller_id": CONTROLLER_ID,
        "plan_name": name,
        "plan_path": str(entry["path"]),
        "plan_sha256": str(entry["sha256"]),
        "git_revision": str(config["expected_git_revision"]),
        "exit_code": 0,
    }
    if any(state.get(key) != value for key, value in expected_state.items()):
        return False, "completion_state_metadata_mismatch"
    if evidence.get("status") != "passed" or evidence.get("plan_sha256") != entry["sha256"]:
        return False, "completion_evidence_metadata_mismatch"
    if Path(str(state.get("evidence", ""))).resolve() != evidence_path:
        return False, "completion_evidence_path_mismatch"
    if not evidence_path.is_file() or sha256_file(evidence_path) != state.get("evidence_sha256"):
        return False, "completion_evidence_hash_mismatch"
    raw_relative = Path(str(state.get("raw_log", "")))
    raw_log = (root / raw_relative).resolve()
    if raw_relative.is_absolute() or raw_log == root or root not in raw_log.parents:
        return False, "completion_raw_log_path_invalid"
    if not raw_log.is_file() or sha256_file(raw_log) != state.get("raw_log_sha256"):
        return False, "completion_raw_log_hash_mismatch"
    evidence_raw = evidence.get("raw_log")
    if not isinstance(evidence_raw, dict):
        return False, "completion_evidence_raw_log_missing"
    if evidence_raw.get("path") != str(raw_relative):
        return False, "completion_raw_log_reference_mismatch"
    if evidence_raw.get("sha256") != state.get("raw_log_sha256"):
        return False, "completion_raw_log_evidence_hash_mismatch"
    return True, "passed"


def _worker_identity_alive(state: dict[str, Any], root: Path) -> bool:
    try:
        pid = int(state["worker_pid"])
        create_time = float(state["worker_create_time"])
        process = psutil.Process(pid)
        return (
            process.is_running()
            and process.status() != psutil.STATUS_ZOMBIE
            and abs(process.create_time() - create_time) <= 1e-3
            and process.cwd() == str(root)
            and tuple(process.cmdline()) == tuple(state["worker_cmdline"])
        )
    except (KeyError, TypeError, ValueError, OSError, psutil.Error):
        return False


def _await_parent_launch_ticket(
    state_path: Path, base_state: dict[str, Any], root: Path, timeout_seconds: float = 30.0
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        state = _read_json(state_path)
        if (
            state is not None
            and state.get("status") == "running"
            and state.get("worker_pid") == base_state["worker_pid"]
            and state.get("worker_create_time") == base_state["worker_create_time"]
            and state.get("worker_cmdline") == base_state["worker_cmdline"]
            and _worker_identity_alive(state, root)
        ):
            return True
        time.sleep(0.05)
    return False


def _active_project_evals(root: Path) -> int:
    count = 0
    for process in psutil.process_iter(("pid", "cmdline")):
        try:
            command = tuple(process.cmdline())
            if (
                process.pid != os.getpid()
                and process.cwd() == str(root)
                and "eval" in command
                and any(
                    "interactive_verification.py@interactive_verification" in part
                    for part in command
                )
            ):
                count += 1
        except (OSError, psutil.Error):
            continue
    return count


def _write_report(state_dir: Path, report: dict[str, Any]) -> None:
    report["checked_at_unix"] = time.time()
    atomic_write_json(state_dir / "latest.json", report)
    append_jsonl(state_dir / "events.jsonl", report)


def _analysis_command(
    plan: dict[str, Any],
    raw_log: Path,
    plan_hash: str,
    revision: str,
    evidence: Path,
) -> list[str]:
    value = plan.get("analysis_command")
    if not isinstance(value, list) or not all(isinstance(part, str) for part in value):
        raise ValueError("plan analysis_command is invalid")
    command = list(value)
    command[0] = sys.executable
    run_log_positions = [index for index, part in enumerate(command) if part.endswith("/RUN.eval")]
    if len(run_log_positions) != 1:
        raise ValueError("analysis command must contain one RUN.eval placeholder")
    command[run_log_positions[0]] = str(raw_log)
    command = [
        plan_hash if part == "PLAN_SHA256" else revision if part == "GIT_REVISION" else part
        for part in command
    ]
    output_positions = [index for index, part in enumerate(command) if part == "--output"]
    if len(output_positions) != 1 or output_positions[0] + 1 >= len(command):
        raise ValueError("analysis command must contain exactly one output")
    command[output_positions[0] + 1] = str(evidence)
    return command


def _worker(config_path: Path, plan_name: str) -> int:
    config, root, state_dir = _load_config(config_path)
    _verify_controller_identity(config, root)
    entries = _plan_entries(config, root)
    matches = [entry for entry in entries if entry["name"] == plan_name]
    if len(matches) != 1:
        raise ValueError("worker plan is not in the allowlisted queue")
    entry = matches[0]
    plan_path = Path(entry["resolved_path"])
    plan = _object(yaml.safe_load(plan_path.read_text(encoding="utf-8")), "plan")
    state_path = _state_path(state_dir, plan_name)
    evidence = _evidence_path(state_dir, plan_name)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    process = psutil.Process(os.getpid())
    base_state = {
        "schema_version": "1.0.0",
        "controller_id": config.get("controller_id"),
        "plan_name": plan_name,
        "plan_path": str(entry["path"]),
        "plan_sha256": entry["sha256"],
        "worker_pid": process.pid,
        "worker_create_time": process.create_time(),
        "worker_cmdline": process.cmdline(),
        "git_revision": _git_revision(root),
    }
    if not _await_parent_launch_ticket(state_path, base_state, root):
        print("parent launch ticket was not established", file=sys.stderr)
        return 70
    monitor = _run_monitor(config, root)
    if monitor.get("exit_code") != 0 or monitor.get("healthy") is not True:
        atomic_write_json(
            state_path,
            {
                **base_state,
                "status": "pending",
                "reason": "monitor_unhealthy_at_worker",
                "monitor": monitor,
            },
        )
        return 0
    if _active_project_evals(root):
        atomic_write_json(
            state_path,
            {**base_state, "status": "pending", "reason": "project_eval_started_before_worker"},
        )
        return 0
    minimum_mib = int(float(config.get("minimum_free_gpu_memory_gib", 45)) * 1024)
    readings = _stable_gpu_readings(config)
    if min(readings) < minimum_mib:
        atomic_write_json(
            state_path,
            {
                **base_state,
                "status": "pending",
                "reason": "gpu_memory_changed_before_worker_launch",
                "free_memory_mib": readings,
                "minimum_free_memory_mib": minimum_mib,
            },
        )
        return 0
    input_errors = validate_frozen_execution_inputs(plan, root)
    if input_errors:
        atomic_write_json(
            state_path,
            {
                **base_state,
                "status": "frozen_input_gate_failed_at_worker",
                "input_errors": list(input_errors),
            },
        )
        return 1
    final_readings = _stable_gpu_readings(config)
    if min(final_readings) < minimum_mib:
        atomic_write_json(
            state_path,
            {
                **base_state,
                "status": "pending",
                "reason": "gpu_memory_changed_during_worker_input_validation",
                "free_memory_mib": final_readings,
                "minimum_free_memory_mib": minimum_mib,
            },
        )
        return 0
    if _active_project_evals(root):
        atomic_write_json(
            state_path,
            {**base_state, "status": "pending", "reason": "project_eval_started_during_gate"},
        )
        return 0
    log_dir = _plan_log_directory(root, plan)
    before = set(log_dir.glob("*.eval")) if log_dir.is_dir() else set()
    if before:
        atomic_write_json(
            state_path,
            {**base_state, "status": "blocked_existing_log_at_worker"},
        )
        return 1
    if evidence.exists():
        atomic_write_json(
            state_path,
            {**base_state, "status": "blocked_existing_evidence_at_worker"},
        )
        return 1
    executable = Path(str(config.get("provtrust_executable", ""))).resolve()
    allocation = _project_file(root, config.get("allocation"), "allocation")
    run = subprocess.run(
        [
            str(executable),
            "run-plan",
            "--config",
            str(plan_path),
            "--no-dry-run",
            "--allocation",
            str(allocation),
        ],
        cwd=root,
        check=False,
    )
    if run.returncode != 0:
        atomic_write_json(
            state_path,
            {**base_state, "status": "execution_failed", "exit_code": run.returncode},
        )
        return run.returncode
    after = set(log_dir.glob("*.eval")) if log_dir.is_dir() else set()
    created = sorted(after - before)
    if len(created) != 1:
        atomic_write_json(
            state_path,
            {
                **base_state,
                "status": "log_cardinality_failed",
                "new_log_count": len(created),
            },
        )
        return 1
    analysis = subprocess.run(
        _analysis_command(
            plan,
            created[0],
            str(entry["sha256"]),
            str(base_state["git_revision"]),
            evidence,
        ),
        cwd=root,
        check=False,
    )
    evidence_value = _read_json(evidence)
    passed = (
        analysis.returncode == 0
        and evidence_value is not None
        and evidence_value.get("status") == "passed"
        and evidence_value.get("plan_sha256") == entry["sha256"]
    )
    atomic_write_json(
        state_path,
        {
            **base_state,
            "status": "passed" if passed else "validation_failed",
            "exit_code": analysis.returncode,
            "raw_log": str(created[0].relative_to(root)),
            "raw_log_sha256": sha256_file(created[0]),
            "evidence": str(evidence),
            "evidence_sha256": sha256_file(evidence) if evidence.is_file() else None,
            "prelaunch_free_memory_mib": final_readings,
            "monitor": monitor,
        },
    )
    return 0 if passed else 1


def _once(config_path: Path) -> int:
    config, root, state_dir = _load_config(config_path)
    lock_path = state_dir / "controller.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            report = {"status": "busy", "action": "none", "reason": "controller_locked"}
            _write_report(state_dir, report)
            print(json.dumps(report, indent=2))
            return 0

        controller = _verify_controller_identity(config, root)
        revision = _git_revision(root)
        monitor = _run_monitor(config, root)
        if monitor.get("exit_code") != 0 or monitor.get("healthy") is not True:
            report = {
                "status": "blocked",
                "action": "none",
                "reason": "monitor_unhealthy",
                "monitor": monitor,
            }
            _write_report(state_dir, report)
            print(json.dumps(report, indent=2))
            return 1

        entries = _plan_entries(config, root)
        passed_names: list[str] = []
        pending: dict[str, Any] | None = None
        for entry in entries:
            name = str(entry["name"])
            evidence_path = _evidence_path(state_dir, name)
            state_path = _state_path(state_dir, name)
            evidence = _read_json(evidence_path)
            state = _read_json(state_path)
            if state_path.exists() and state is None:
                report = {
                    "status": "blocked",
                    "action": "none",
                    "reason": "unreadable_plan_state",
                    "plan": name,
                    "monitor": monitor,
                }
                _write_report(state_dir, report)
                print(json.dumps(report, indent=2))
                return 1
            if state is not None and state.get("status") == "running":
                if _worker_identity_alive(state, root):
                    report = {
                        "status": "running",
                        "action": "none",
                        "plan": name,
                        "passed_plans": passed_names,
                        "worker_pid": state.get("worker_pid"),
                        "monitor": monitor,
                    }
                    _write_report(state_dir, report)
                    print(json.dumps(report, indent=2))
                    return 0
                report = {
                    "status": "blocked",
                    "action": "none",
                    "reason": "worker_identity_lost",
                    "plan": name,
                    "monitor": monitor,
                }
                _write_report(state_dir, report)
                print(json.dumps(report, indent=2))
                return 1
            if evidence_path.exists() or (state is not None and state.get("status") == "passed"):
                complete, reason = _completed_entry_valid(
                    config, root, state_dir, entry, state, evidence
                )
                if complete:
                    passed_names.append(name)
                    continue
                report = {
                    "status": "blocked",
                    "action": "none",
                    "reason": reason,
                    "plan": name,
                    "monitor": monitor,
                }
                _write_report(state_dir, report)
                print(json.dumps(report, indent=2))
                return 1
            if state is not None and state.get("status") not in {None, "pending"}:
                report = {
                    "status": "blocked",
                    "action": "none",
                    "reason": str(state.get("status")),
                    "plan": name,
                    "monitor": monitor,
                }
                _write_report(state_dir, report)
                print(json.dumps(report, indent=2))
                return 1
            pending = entry
            break

        if pending is None:
            report = {
                "status": "complete",
                "action": "none",
                "passed_plans": passed_names,
                "monitor": monitor,
            }
            _write_report(state_dir, report)
            print(json.dumps(report, indent=2))
            return 0

        name = str(pending["name"])
        plan_path = Path(pending["resolved_path"])
        plan = _object(yaml.safe_load(plan_path.read_text(encoding="utf-8")), "plan")
        log_dir = _plan_log_directory(root, plan)
        existing_logs = sorted(log_dir.glob("*.eval")) if log_dir.is_dir() else []
        if existing_logs:
            report = {
                "status": "blocked",
                "action": "none",
                "reason": "unadjudicated_existing_log",
                "plan": name,
                "log_count": len(existing_logs),
                "monitor": monitor,
            }
            _write_report(state_dir, report)
            print(json.dumps(report, indent=2))
            return 1
        active = _active_project_evals(root)
        if active:
            report = {
                "status": "deferred",
                "action": "none",
                "reason": "project_eval_already_running",
                "active_project_evals": active,
                "plan": name,
                "monitor": monitor,
            }
            _write_report(state_dir, report)
            print(json.dumps(report, indent=2))
            return 0

        minimum_mib = int(float(config.get("minimum_free_gpu_memory_gib", 45)) * 1024)
        readings = _stable_gpu_readings(config)
        if min(readings) < minimum_mib:
            report = {
                "status": "deferred",
                "action": "none",
                "reason": "insufficient_stable_gpu_memory",
                "plan": name,
                "physical_gpu_index": config.get("physical_gpu_index"),
                "free_memory_mib": readings,
                "minimum_free_memory_mib": minimum_mib,
                "passed_plans": passed_names,
                "monitor": monitor,
            }
            _write_report(state_dir, report)
            print(json.dumps(report, indent=2))
            return 0

        input_errors = validate_frozen_execution_inputs(plan, root)
        if input_errors:
            report = {
                "status": "blocked",
                "action": "none",
                "reason": "frozen_input_gate_failed",
                "plan": name,
                "input_errors": list(input_errors),
                "monitor": monitor,
            }
            _write_report(state_dir, report)
            print(json.dumps(report, indent=2))
            return 1
        final_readings = _stable_gpu_readings(config)
        if min(final_readings) < minimum_mib:
            report = {
                "status": "deferred",
                "action": "none",
                "reason": "gpu_memory_changed_during_input_validation",
                "plan": name,
                "free_memory_mib": final_readings,
                "minimum_free_memory_mib": minimum_mib,
                "monitor": monitor,
            }
            _write_report(state_dir, report)
            print(json.dumps(report, indent=2))
            return 0
        active = _active_project_evals(root)
        if active:
            report = {
                "status": "deferred",
                "action": "none",
                "reason": "project_eval_started_during_input_validation",
                "active_project_evals": active,
                "plan": name,
                "monitor": monitor,
            }
            _write_report(state_dir, report)
            print(json.dumps(report, indent=2))
            return 0

        stdout_dir = state_dir / "worker-logs"
        stdout_dir.mkdir(parents=True, exist_ok=True)
        stdout_dir.chmod(0o700)
        stdout_path = stdout_dir / f"{name}.log"
        python_executable = Path(str(config.get("python_executable", ""))).resolve()
        if not python_executable.is_file():
            raise ValueError("python_executable is missing")
        command = [
            str(python_executable),
            str(controller),
            "--config",
            str(config_path.resolve()),
            "--worker-plan",
            name,
        ]
        worker_pid: int | None = None
        try:
            with stdout_path.open("ab") as output:
                stdout_path.chmod(0o600)
                worker = subprocess.Popen(
                    command,
                    cwd=root,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            worker_pid = worker.pid
            process = psutil.Process(worker.pid)
            state = {
                "schema_version": "1.0.0",
                "status": "running",
                "controller_id": config.get("controller_id"),
                "plan_name": name,
                "plan_path": str(pending["path"]),
                "plan_sha256": pending["sha256"],
                "worker_pid": worker.pid,
                "worker_create_time": process.create_time(),
                "worker_cmdline": process.cmdline(),
                "git_revision": revision,
                "worker_log": str(stdout_path),
            }
            atomic_write_json(_state_path(state_dir, name), state)
        except (OSError, psutil.Error) as error:
            failure = {
                "schema_version": "1.0.0",
                "status": "worker_launch_failed",
                "controller_id": config.get("controller_id"),
                "plan_name": name,
                "plan_path": str(pending["path"]),
                "plan_sha256": pending["sha256"],
                "worker_pid": worker_pid,
                "git_revision": revision,
                "error_type": type(error).__name__,
            }
            atomic_write_json(_state_path(state_dir, name), failure)
            report = {
                "status": "blocked",
                "action": "none",
                "reason": "worker_launch_failed",
                "plan": name,
                "worker_pid": worker_pid,
                "monitor": monitor,
            }
            _write_report(state_dir, report)
            print(json.dumps(report, indent=2))
            return 1
        report = {
            "status": "running",
            "action": "started",
            "plan": name,
            "worker_pid": worker_pid,
            "free_memory_mib": final_readings,
            "minimum_free_memory_mib": minimum_mib,
            "passed_plans": passed_names,
            "monitor": monitor,
        }
        _write_report(state_dir, report)
        print(json.dumps(report, indent=2))
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--worker-plan")
    args = parser.parse_args()
    if args.once == (args.worker_plan is not None):
        raise ValueError("select exactly one of --once or --worker-plan")
    if args.worker_plan is not None:
        return _worker(args.config, args.worker_plan)
    return _once(args.config)


if __name__ == "__main__":
    raise SystemExit(main())
