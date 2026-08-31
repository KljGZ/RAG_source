"""Repository-level scientific, safety, and reproducibility audit."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict


class AuditReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checks: dict[str, bool]

    @property
    def passed(self) -> bool:
        return not self.errors


REQUIRED_PATHS = (
    "SCIENTIFIC_REGISTER.yaml",
    "EXPERIMENT_PLAN.lock.yaml",
    "third_party/THIRD_PARTY_MANIFEST.yaml",
    "docs/THREAT_MODEL.md",
    "docs/ETHICS.md",
    "docs/RUNBOOK.md",
    "docs/DEPLOYMENT_AUDIT.md",
    "artifacts/system/RESOURCE_PLAN.md",
    "benchmark/schemas/MANIFEST.json",
    "benchmark/manifests/smoke.yaml",
    "prompts/frozen/MANIFEST.json",
    "environments/locks/LOCKS.sha256",
    "configs/clusters/allocation.example.yaml",
    "configs/monitoring/remote.example.yaml",
    "src/provtrust/schemas/trial.py",
    "src/provtrust/defense/pavg_agent.py",
    "web_env/search_index/documents.jsonl",
)

SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|password|secret|authorization)[ \t]*[:=][ \t]*['\"]?[A-Za-z0-9_./+-]{12,}"
)


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML object: {path}")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_contained(base: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise ValueError(f"path must be nonempty and relative: {relative!r}")
    base = base.resolve()
    target = (base / relative).resolve()
    if target == base or base not in target.parents:
        raise ValueError(f"path escapes its declared root: {relative}")
    return target


def _verify_hash_entries(*, base: Path, entries: Any, entry_label: str) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if not isinstance(entries, list) or not entries:
        return False, [f"{entry_label} entries must be a nonempty list"]
    observed_paths: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            failures.append(f"{entry_label}[{index}] is not an object")
            continue
        relative = entry.get("path")
        expected = entry.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            failures.append(f"{entry_label}[{index}] lacks string path/sha256")
            continue
        if relative in observed_paths:
            failures.append(f"{entry_label} repeats path: {relative}")
            continue
        observed_paths.add(relative)
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            failures.append(f"{entry_label} has invalid SHA-256: {relative}")
            continue
        try:
            target = _resolve_contained(base, relative)
        except ValueError as error:
            failures.append(str(error))
            continue
        if not target.is_file():
            failures.append(f"{entry_label} target missing: {relative}")
        elif _sha256(target) != expected:
            failures.append(f"{entry_label} hash mismatch: {relative}")
    return not failures, failures


def _audit_lock_manifest(root: Path) -> tuple[bool, list[str]]:
    manifest = root / "environments/locks/LOCKS.sha256"
    failures: list[str] = []
    seen: set[str] = set()
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        expected, separator, relative = line.partition("  ")
        if (
            not separator
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
            or not relative
            or relative in seen
        ):
            failures.append(f"invalid or duplicate lock entry on line {line_number}")
            continue
        seen.add(relative)
        try:
            target = _resolve_contained(manifest.parent, relative)
        except ValueError as error:
            failures.append(str(error))
            continue
        if not target.is_file():
            failures.append(f"lock target missing: {relative}")
        elif _sha256(target) != expected:
            failures.append(f"lock hash mismatch: {relative}")
    if not seen:
        failures.append("environment lock manifest is empty")
    return not failures, failures


def _audit_frozen_manifests(root: Path) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    failures: list[str] = []

    prompts = _load_json(root / "prompts/frozen/MANIFEST.json")
    prompt_ok, prompt_failures = _verify_hash_entries(
        base=root, entries=prompts.get("prompts"), entry_label="prompt manifest"
    )
    checks["frozen_prompt_hashes"] = prompt_ok
    failures.extend(prompt_failures)

    schema_path = root / "benchmark/schemas/MANIFEST.json"
    schemas = _load_json(schema_path)
    schema_ok, schema_failures = _verify_hash_entries(
        base=schema_path.parent,
        entries=schemas.get("schemas"),
        entry_label="schema manifest",
    )
    manifest_digest = schemas.get("manifest_content_sha256")
    unhashed = {key: value for key, value in schemas.items() if key != "manifest_content_sha256"}
    canonical = json.dumps(unhashed, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    self_hash_ok = (
        isinstance(manifest_digest, str)
        and hashlib.sha256(canonical.encode("utf-8")).hexdigest() == manifest_digest
    )
    checks["frozen_schema_hashes"] = schema_ok and self_hash_ok
    failures.extend(schema_failures)
    if not self_hash_ok:
        failures.append("schema manifest content hash mismatch")

    smoke = _load_yaml(root / "benchmark/manifests/smoke.yaml")
    smoke_path = smoke.get("path")
    smoke_digest = smoke.get("sha256")
    smoke_ok = False
    if isinstance(smoke_path, str) and isinstance(smoke_digest, str):
        target = _resolve_contained(root, smoke_path)
        smoke_ok = target.is_file() and _sha256(target) == smoke_digest
    checks["smoke_dataset_hash"] = smoke_ok
    if not smoke_ok:
        failures.append("smoke dataset manifest hash mismatch")
    return checks, failures


def _audit_resource_gates(root: Path) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    experiment_paths = sorted((root / "configs/experiments").glob("*.yaml"))
    gated = bool(experiment_paths)
    requirements_valid = bool(experiment_paths)
    for path in experiment_paths:
        value = _load_yaml(path)
        gated = gated and value.get("resource_allocation_required") is True
        execution_status = value.get("execution_status")
        if execution_status not in {
            "ready",
            "blocked_pending_resources_and_frozen_inputs",
            "blocked_until_experiment_plan_frozen",
        }:
            requirements_valid = False
            failures.append(f"experiment has invalid execution_status: {path.name}")
        minimum = value.get("minimum_resources")
        if not isinstance(minimum, dict):
            requirements_valid = False
            failures.append(f"experiment lacks minimum_resources: {path.name}")
            continue
        required_positive = ("cpu_cores", "ram_gib", "storage_gib")
        numeric_ok = all(
            isinstance(minimum.get(key), (int, float))
            and not isinstance(minimum.get(key), bool)
            and float(minimum[key]) > 0
            for key in required_positive
        )
        gpu_ok = (
            isinstance(minimum.get("gpu_count"), int)
            and not isinstance(minimum.get("gpu_count"), bool)
            and int(minimum["gpu_count"]) >= 0
        )
        command = value.get("inspect_command")
        command_ok = (
            isinstance(command, list)
            and len(command) >= 2
            and command[0] == "inspect"
            and all(isinstance(part, str) for part in command)
        )
        requirements_valid = requirements_valid and numeric_ok and gpu_ok and command_ok
        if not (numeric_ok and gpu_ok and command_ok):
            failures.append(f"invalid resource or command contract: {path.name}")
    checks["all_experiments_resource_gated"] = gated
    checks["experiment_resource_contracts"] = requirements_valid
    if not gated:
        failures.append("every experiment config must require reviewed resource allocation")

    allocation = _load_yaml(root / "configs/clusters/allocation.example.yaml")
    allocation_safe = allocation.get("approved") is False and not allocation.get("gpu_indices")
    checks["example_allocation_unapproved"] = allocation_safe
    if not allocation_safe:
        failures.append("example allocation must be unapproved and contain no GPU indices")

    plan = _load_yaml(root / "EXPERIMENT_PLAN.lock.yaml")
    v1_unfrozen = plan.get("status") == "draft_not_frozen"
    checks["confirmatory_plan_not_prematurely_frozen"] = v1_unfrozen
    if not v1_unfrozen:
        failures.append("confirmatory plan status changed without the formal freeze workflow")
    return checks, failures


def _audit_monitor_template(root: Path) -> tuple[bool, list[str]]:
    value = _load_yaml(root / "configs/monitoring/remote.example.yaml")
    failures: list[str] = []
    processes = value.get("processes")
    if not isinstance(processes, list) or not processes:
        return False, ["monitor template has no process allowlist"]
    for index, process in enumerate(processes):
        if not isinstance(process, dict):
            failures.append(f"monitor process {index} is not an object")
            continue
        command = process.get("command")
        enabled = process.get("enabled") is True
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            failures.append(f"monitor process {index} has an invalid command")
            continue
        lowered = " ".join(command).lower()
        if enabled and ("inspect" in lowered or " eval" in lowered or "python" in lowered):
            failures.append(f"enabled monitor process may start an experiment: {index}")
        if enabled and not ("provtrust" in command[0] and "serve" in command):
            failures.append(
                f"enabled monitor process is not an allowlisted source service: {index}"
            )
        health = process.get("health")
        url = health.get("url") if isinstance(health, dict) else None
        if isinstance(url, str) and not url.startswith(("http://127.0.0.1:", "http://localhost:")):
            failures.append(f"monitor health URL is not loopback-only: {index}")
    return not failures, failures


def audit_repository(root: Path) -> AuditReport:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}
    missing = [path for path in REQUIRED_PATHS if not (root / path).exists()]
    checks["required_paths"] = not missing
    if missing:
        errors.append(f"required paths missing: {missing}")
        return AuditReport(errors=tuple(errors), warnings=(), checks=dict(sorted(checks.items())))
    try:
        scientific = _load_yaml(root / "SCIENTIFIC_REGISTER.yaml")
        required_normative = {
            "claim_conditioned_reliability",
            "identity_authenticity",
            "attribution_authenticity",
            "evidence_warrant",
            "source_independence",
            "completed_verification",
        }
        observed = set(scientific.get("normative_variables", []))
        checks["six_normative_variables"] = observed == required_normative
        if observed != required_normative:
            errors.append("scientific register does not contain exactly six normative variables")
        axioms = scientific.get("axioms", {})
        checks["eight_axioms"] = isinstance(axioms, dict) and len(axioms) == 8
        if not checks["eight_axioms"]:
            errors.append("scientific register must contain eight normative axioms")
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        errors.append(f"scientific register invalid: {error}")
    try:
        third_party = _load_yaml(root / "third_party/THIRD_PARTY_MANIFEST.yaml")
        unsafe_copy = [
            row.get("id")
            for row in third_party.get("resources", [])
            if row.get("license") == "NO-LICENSE-DETECTED" and row.get("copy_code")
        ]
        checks["unlicensed_code_not_copied"] = not unsafe_copy
        if unsafe_copy:
            errors.append(f"unlicensed repositories marked for code copying: {unsafe_copy}")
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        errors.append(f"third-party manifest invalid: {error}")
    try:
        locks_ok, lock_failures = _audit_lock_manifest(root)
        checks["environment_lock_hashes"] = locks_ok
        errors.extend(lock_failures)
    except (OSError, TypeError, ValueError) as error:
        checks["environment_lock_hashes"] = False
        errors.append(f"environment lock manifest invalid: {error}")
    try:
        frozen_checks, frozen_failures = _audit_frozen_manifests(root)
        checks.update(frozen_checks)
        errors.extend(frozen_failures)
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as error:
        errors.append(f"frozen artifact manifest invalid: {error}")
    try:
        gate_checks, gate_failures = _audit_resource_gates(root)
        checks.update(gate_checks)
        errors.extend(gate_failures)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        errors.append(f"resource gate invalid: {error}")
    try:
        monitor_ok, monitor_failures = _audit_monitor_template(root)
        checks["monitor_allowlist_safe"] = monitor_ok
        errors.extend(monitor_failures)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        checks["monitor_allowlist_safe"] = False
        errors.append(f"monitor template invalid: {error}")
    try:
        tracked = (
            subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True)
            .stdout.decode("utf-8")
            .split("\0")
        )
        suspect_files: list[str] = []
        for relative in tracked:
            if not relative or relative.endswith((".png", ".pdf", ".lock")):
                continue
            path = root / relative
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if SECRET_PATTERN.search(text):
                suspect_files.append(relative)
        checks["tracked_secret_scan"] = not suspect_files
        if suspect_files:
            errors.append(f"possible tracked secrets: {suspect_files}")
    except (subprocess.SubprocessError, UnicodeDecodeError) as error:
        warnings.append(f"tracked-secret scan unavailable: {error}")
        checks["tracked_secret_scan"] = False
    index_path = root / "web_env/search_index/documents.jsonl"
    if index_path.is_file():
        unsafe_urls: list[str] = []
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            url = str(json.loads(line)["controlled_url"])
            if not url.startswith(("http://127.0.0.1:", "http://localhost:")):
                unsafe_urls.append(url)
        checks["controlled_urls_loopback"] = not unsafe_urls
        if unsafe_urls:
            errors.append(f"non-loopback controlled URLs: {unsafe_urls}")
    return AuditReport(
        errors=tuple(errors), warnings=tuple(warnings), checks=dict(sorted(checks.items()))
    )
