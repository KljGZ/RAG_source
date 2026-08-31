from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED_MODULES = (
    "inspect_ai",
    "pydantic",
    "pyarrow",
    "duckdb",
    "polars",
    "networkx",
    "httpx",
    "sklearn",
    "scipy",
    "statsmodels",
    "pytest",
    "provtrust",
)


def module_version(name: str) -> str:
    module = importlib.import_module(name)
    return str(getattr(module, "__version__", "unknown"))


def gpu_inventory() -> list[str]:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return []
    result = subprocess.run(
        [
            executable,
            "--query-gpu=index,name,driver_version,memory.total,compute_cap",
            "--format=csv,noheader",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    versions: dict[str, str] = {}
    failures: dict[str, str] = {}
    for name in REQUIRED_MODULES:
        try:
            versions[name] = module_version(name)
        except Exception as exc:  # noqa: BLE001 - audit all import failures
            failures[name] = f"{type(exc).__name__}: {exc}"

    report = {
        "schema_version": "1.0.0",
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "conda_prefix": os.environ.get("CONDA_PREFIX"),
        "modules": versions,
        "failures": failures,
        "gpus": gpu_inventory(),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
