"""Export a portable, hash-preserving record of an installed environment."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packaging.utils import canonicalize_name

CONDA_FORGE_BASE = "https://conda.anaconda.org/conda-forge"
PROJECT_DISTRIBUTIONS = {"provenance-trust-bench"}


def portable_conda_url(record: dict[str, Any]) -> str:
    url = str(record.get("url") or "")
    channel = str(record.get("channel") or "")
    filename = str(record.get("fn") or "")
    subdir = str(record.get("subdir") or "")
    if filename and subdir and (url.startswith("file:") or channel == "<unknown>" or not url):
        return f"{CONDA_FORGE_BASE}/{subdir}/{filename}"
    return url


def conda_records(prefix: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted((prefix / "conda-meta").glob("*.json")):
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        records.append(
            {
                "name": raw.get("name"),
                "version": raw.get("version"),
                "build": raw.get("build"),
                "build_number": raw.get("build_number"),
                "subdir": raw.get("subdir"),
                "filename": raw.get("fn"),
                "url": portable_conda_url(raw),
                "sha256": raw.get("sha256"),
                "md5": raw.get("md5"),
            }
        )
    return records


def pip_records() -> list[dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for distribution in importlib.metadata.distributions():
        name = canonicalize_name(distribution.metadata.get("Name", ""))
        installer = (distribution.read_text("INSTALLER") or "").strip()
        if not name or name in PROJECT_DISTRIBUTIONS or installer != "pip":
            continue
        records[name] = {
            "name": name,
            "version": distribution.version,
            "installer": installer,
        }
    return [records[name] for name in sorted(records)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pip-lock", type=Path, required=True)
    args = parser.parse_args()
    conda = conda_records(args.prefix)
    pip = pip_records()
    report = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "prefix_name": args.prefix.name,
        "python": sys.version,
        "platform": platform.platform(),
        "conda_package_count": len(conda),
        "pip_package_count": len(pip),
        "conda_packages": conda,
        "pip_packages": pip,
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.pip_lock.write_text(
        "".join(f"{record['name']}=={record['version']}\n" for record in pip),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
