"""Verify pinned third-party HEADs without cloning or executing their code."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


def load_manifest(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("resources"), list):
        raise TypeError("invalid third-party manifest")
    return data


def remote_head(url: str) -> str:
    result = subprocess.run(
        ["git", "-c", "http.sslBackend=openssl", "ls-remote", f"{url}.git", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.split()[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", type=Path, default=Path("third_party/THIRD_PARTY_MANIFEST.yaml")
    )
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    report: list[dict[str, Any]] = []
    for resource in manifest["resources"]:
        row = {
            "id": resource["id"],
            "pinned_commit": resource["commit"],
            "license": resource["license"],
            "copy_code": resource["copy_code"],
        }
        if args.online:
            row["current_head"] = remote_head(resource["url"])
            row["head_matches_pin"] = row["current_head"] == row["pinned_commit"]
        report.append(row)
    print(json.dumps({"schema_version": "1.0.0", "resources": report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
