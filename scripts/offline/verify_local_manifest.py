"""Verify a filename/SHA-256/size TSV without trusting external URLs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from download_manifest import digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    records: list[dict[str, object]] = []
    valid = True
    names: set[str] = set()
    for number, raw in enumerate(args.manifest.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 3:
            raise ValueError(f"{args.manifest}:{number}: expected filename, SHA-256, size")
        filename, expected_hash, size_text = fields
        if Path(filename).name != filename or filename in names:
            raise ValueError(f"{args.manifest}:{number}: unsafe or duplicate filename")
        names.add(filename)
        expected_size = int(size_text)
        path = args.directory / filename
        if path.is_file():
            actual_hash, actual_size = digest(path)
        else:
            actual_hash, actual_size = "", -1
        item_valid = expected_hash == actual_hash and expected_size == actual_size
        valid = valid and item_valid
        records.append(
            {
                "filename": filename,
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "expected_size": expected_size,
                "actual_size": actual_size,
                "valid": item_valid,
            }
        )
    report = {
        "schema_version": "1.0.0",
        "valid": valid,
        "manifest": str(args.manifest.resolve()),
        "directory": str(args.directory.resolve()),
        "files": records,
    }
    output = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
