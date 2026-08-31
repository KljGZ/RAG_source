"""Build a filename/SHA-256/size TSV for files already downloaded locally."""

from __future__ import annotations

import argparse
from pathlib import Path

from download_manifest import digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--glob", default="*")
    args = parser.parse_args()
    files = sorted(path for path in args.directory.glob(args.glob) if path.is_file())
    if not files:
        parser.error("no matching files")
    lines = ["# filename\tsha256\tsize"]
    for path in files:
        sha256, size = digest(path)
        lines.append(f"{path.name}\t{sha256}\t{size}")
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
