#!/usr/bin/env python3
"""Verify every file named by an offline TSV manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from download_manifest import digest, parse_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    results: list[dict[str, object]] = []
    valid = True
    for entry in parse_manifest(args.manifest):
        path = args.directory / entry.filename
        if path.is_file():
            actual_hash, actual_size = digest(path)
        else:
            actual_hash, actual_size = "", -1
        item_valid = actual_hash == entry.sha256 and actual_size == entry.size
        valid = valid and item_valid
        results.append(
            {
                "filename": entry.filename,
                "expected_sha256": entry.sha256,
                "actual_sha256": actual_hash,
                "expected_size": entry.size,
                "actual_size": actual_size,
                "valid": item_valid,
            }
        )
    report = {
        "schema_version": "1.0.0",
        "valid": valid,
        "manifest": str(args.manifest.resolve()),
        "directory": str(args.directory.resolve()),
        "files": results,
    }
    output = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
