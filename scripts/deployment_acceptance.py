"""Produce a no-GPU-allocation deployment acceptance record.

The script inspects package metadata and ``nvidia-smi`` inventory only. It never
imports torch, creates a CUDA context, loads a model, or starts an experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import psutil

from provtrust.execution.atomic_io import atomic_write_json

PYTHON_PACKAGES = {
    "provenance-trust-bench": "0.1.0",
    "inspect-ai": "0.3.261",
    "browsergym-core": "0.14.3",
    "playwright": "1.44.0",
    "trafilatura": "2.0.0",
    "transformers": "4.56.2",
    "sentence-transformers": "5.1.0",
    "torch": "2.12.1+cu130",
    "cuda-toolkit": "13.0.2",
    "cuda-bindings": "13.0.3",
    "nvidia-cudnn-cu13": "9.20.0.48",
    "nvidia-nccl-cu13": "2.29.7",
    "triton": "3.7.1",
}

R_PACKAGES = {
    "R": "4.5.3",
    "arrow": "25.0.0",
    "clubSandwich": "0.7.0",
    "emmeans": "2.0.4",
    "glmmTMB": "1.1.14",
    "lme4": "2.0-6",
    "targets": "1.12.0",
    "TOSTER": "0.8.6",
}


def run_command(command: list[str], *, cwd: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=120)
        return {
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "passed": result.returncode == 0,
        }
    except (OSError, subprocess.SubprocessError) as error:
        return {
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(error).__name__}: {error}",
            "passed": False,
        }


def git_record(root: Path) -> dict[str, Any]:
    head = run_command(["git", "rev-parse", "HEAD"], cwd=root)
    branch = run_command(["git", "branch", "--show-current"], cwd=root)
    status = run_command(["git", "status", "--porcelain"], cwd=root)
    return {
        "head": head["stdout"],
        "branch": branch["stdout"],
        "clean": bool(status["passed"] and not status["stdout"]),
        "checks_passed": bool(head["passed"] and branch["passed"] and status["passed"]),
    }


def python_package_record() -> dict[str, Any]:
    observed: dict[str, str | None] = {}
    mismatches: dict[str, dict[str, str | None]] = {}
    for name, expected in PYTHON_PACKAGES.items():
        try:
            version: str | None = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            version = None
        observed[name] = version
        if version != expected:
            mismatches[name] = {"expected": expected, "observed": version}
    return {
        "observed": observed,
        "expected": PYTHON_PACKAGES,
        "mismatches": mismatches,
        "passed": not mismatches,
        "torch_imported": "torch" in sys.modules,
    }


def r_package_record(root: Path) -> dict[str, Any]:
    rscript = shutil.which("Rscript")
    if rscript is None:
        return {"passed": False, "error": "Rscript_not_found", "observed": {}}
    names = [name for name in R_PACKAGES if name != "R"]
    expression = (
        "cat(paste(c(paste0('R=', getRversion()), "
        + ",".join(f"paste0('{name}=', as.character(packageVersion('{name}')))" for name in names)
        + "), collapse='\\n'))"
    )
    result = run_command([rscript, "-e", expression], cwd=root)
    observed: dict[str, str] = {}
    for line in str(result["stdout"]).splitlines():
        name, separator, version = line.partition("=")
        if separator:
            observed[name] = version
    mismatches = {
        name: {"expected": expected, "observed": observed.get(name)}
        for name, expected in R_PACKAGES.items()
        if observed.get(name) != expected
    }
    return {
        "observed": observed,
        "expected": R_PACKAGES,
        "mismatches": mismatches,
        "command": result,
        "passed": bool(result["passed"] and not mismatches),
    }


def verify_lock_manifest(manifest: Path) -> dict[str, Any]:
    failures: list[str] = []
    checked = 0
    try:
        for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            digest, separator, relative = line.partition("  ")
            if not separator or len(digest) != 64:
                failures.append(f"invalid_line:{line_number}")
                continue
            target = (manifest.parent / relative).resolve()
            if manifest.parent.resolve() not in target.parents or not target.is_file():
                failures.append(f"missing:{relative}")
                continue
            checked += 1
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                failures.append(f"hash_mismatch:{relative}")
    except OSError as error:
        failures.append(f"{type(error).__name__}:{error}")
    return {
        "manifest": str(manifest),
        "checked": checked,
        "failures": failures,
        "passed": not failures,
    }


def browser_record(browser_root: Path, root: Path) -> dict[str, Any]:
    chromium = sorted(browser_root.glob("chromium-*/chrome-linux/chrome"))
    ffmpeg = sorted(browser_root.glob("ffmpeg-*/ffmpeg-linux"))
    chromium_check = (
        run_command([str(chromium[-1]), "--version"], cwd=root)
        if chromium
        else {"passed": False, "stderr": "chromium_not_found"}
    )
    ffmpeg_check = (
        run_command([str(ffmpeg[-1]), "-version"], cwd=root)
        if ffmpeg
        else {"passed": False, "stderr": "ffmpeg_not_found"}
    )
    return {
        "root": str(browser_root),
        "chromium": str(chromium[-1]) if chromium else None,
        "ffmpeg": str(ffmpeg[-1]) if ffmpeg else None,
        "chromium_check": chromium_check,
        "ffmpeg_check": ffmpeg_check,
        "passed": bool(chromium_check["passed"] and ffmpeg_check["passed"]),
    }


def gpu_inventory(root: Path) -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return {"passed": False, "error": "nvidia_smi_not_found", "devices": []}
    result = run_command(
        [
            executable,
            "--query-gpu=index,name,driver_version,memory.total,compute_cap",
            "--format=csv,noheader,nounits",
        ],
        cwd=root,
    )
    return {
        "method": "inventory_only_no_cuda_context",
        "devices": str(result["stdout"]).splitlines(),
        "command": result,
        "passed": result["passed"],
    }


def service_record(urls: list[str]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for url in urls:
        try:
            response = httpx.get(url, timeout=5.0, follow_redirects=False)
            results[url] = {
                "status_code": response.status_code,
                "x_robots_tag": response.headers.get("x-robots-tag"),
                "cache_control": response.headers.get("cache-control"),
                "passed": response.status_code == 200
                and str(response.headers.get("x-robots-tag", "")).startswith("noindex")
                and response.headers.get("cache-control") == "no-store",
            }
        except httpx.HTTPError as error:
            results[url] = {"passed": False, "error": f"{type(error).__name__}: {error}"}
    return {"results": results, "passed": all(value["passed"] for value in results.values())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--browser-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--service-url",
        action="append",
        default=["http://127.0.0.1:18080/healthz", "http://127.0.0.1:18081/healthz"],
    )
    args = parser.parse_args()
    root = args.root.resolve()
    prefix = args.prefix.resolve()
    disk = psutil.disk_usage(root)
    memory = psutil.virtual_memory()
    checks: dict[str, Any] = {
        "git": git_record(root),
        "python_packages": python_package_record(),
        "r_packages": r_package_record(root),
        "environment_locks": verify_lock_manifest(root / "environments/locks/LOCKS.sha256"),
        "browser": browser_record(args.browser_root.resolve(), root),
        "gpu_inventory": gpu_inventory(root),
        "pip_check": run_command([str(prefix / "bin/python"), "-m", "pip", "check"], cwd=root),
        "uv_lock": run_command(
            ["uv", "lock", "--check", "--offline", "--python", str(prefix / "bin/python")],
            cwd=root,
        ),
        "services": service_record(args.service_url),
    }
    passed = all(
        bool(value.get("passed") or value.get("checks_passed")) for value in checks.values()
    )
    report = {
        "schema_version": "1.0.0",
        "captured_at": datetime.now(UTC).isoformat(),
        "stage": "v0_deployment_acceptance",
        "passed": passed,
        "resource_gate": {
            "gpu_probe_executed": False,
            "cuda_context_created": False,
            "model_or_api_call_executed": False,
            "experiments_executed": False,
        },
        "system": {
            "platform": platform.platform(),
            "python": sys.version,
            "python_executable": sys.executable,
            "conda_prefix": os.environ.get("CONDA_PREFIX"),
            "cpu_logical": psutil.cpu_count(logical=True),
            "cpu_physical": psutil.cpu_count(logical=False),
            "memory_total_gib": round(memory.total / (1024**3), 3),
            "disk_total_gib": round(disk.total / (1024**3), 3),
            "disk_free_gib": round(disk.free / (1024**3), 3),
        },
        "checks": checks,
    }
    atomic_write_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
