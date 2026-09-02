"""Build a deterministic content manifest for experiment runtime code."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from provtrust.execution.atomic_io import atomic_write_json, sha256_file


def _contained_file(root: Path, path: Path) -> Path:
    root = root.resolve()
    resolved = path.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"runtime file escapes project root: {path}")
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"runtime file is missing, not regular, or a symlink: {path}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-id", required=True)
    parser.add_argument(
        "--entrypoint",
        default="src/provtrust/tasks/interactive_verification.py",
    )
    args = parser.parse_args()

    root = Path.cwd().resolve()
    source_root = root / "src/provtrust"
    paths = sorted(source_root.rglob("*.py"))
    paths.append(root / "scripts/validate_interactive_preflight.py")
    paths = sorted({_contained_file(root, path) for path in paths})
    entries = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in paths
    ]
    relative_paths = {entry["path"] for entry in entries}
    if args.entrypoint not in relative_paths:
        raise ValueError("entrypoint is not covered by runtime file set")

    builder = Path(__file__).resolve()
    report = {
        "schema_version": "1.0.0",
        "manifest_id": args.manifest_id,
        "purpose": "freeze project code imported by Track E execution and validation",
        "entrypoint": args.entrypoint,
        "builder": {
            "path": builder.relative_to(root).as_posix(),
            "sha256": sha256_file(builder),
        },
        "file_count": len(entries),
        "files": entries,
    }
    artifact_hash = atomic_write_json(args.output, report)
    print(
        json.dumps(
            {
                "status": "passed",
                "output": args.output.as_posix(),
                "sha256": artifact_hash,
                "file_count": len(entries),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
