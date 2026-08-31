"""Create or verify SHA-256 transfer manifests for offline resources."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def safe_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*") if path.is_file() and not path.is_symlink()))


def create(root: Path, output: Path) -> None:
    root = root.resolve()
    records = [
        {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}
        for path in safe_files(root)
        if path.resolve() != output.resolve()
    ]
    output.write_text(
        json.dumps({"schema_version": "1.0.0", "root_name": root.name, "files": records}, indent=2)
        + "\n",
        encoding="utf-8",
    )


def verify(root: Path, manifest: Path) -> int:
    root = root.resolve()
    value = json.loads(manifest.read_text(encoding="utf-8"))
    failures: list[str] = []
    for record in value["files"]:
        target = (root / record["path"]).resolve()
        if root not in target.parents:
            failures.append(f"path_escape:{record['path']}")
        elif not target.is_file():
            failures.append(f"missing:{record['path']}")
        elif target.stat().st_size != record["bytes"] or digest(target) != record["sha256"]:
            failures.append(f"mismatch:{record['path']}")
    print(json.dumps({"verified": not failures, "failures": failures}, indent=2))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("root", type=Path)
    create_parser.add_argument("output", type=Path)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("root", type=Path)
    verify_parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    if args.action == "create":
        create(args.root, args.output)
        return 0
    return verify(args.root, args.manifest)


if __name__ == "__main__":
    raise SystemExit(main())
