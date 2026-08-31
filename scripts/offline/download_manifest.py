#!/usr/bin/env python3
"""Download an HTTPS TSV manifest with deterministic integrity checks.

Each non-comment line has ``url<TAB>sha256<TAB>size``. Duplicate filenames are
accepted only when all metadata match. Files are staged as ``.part`` and moved
into place only after both the declared size and SHA-256 digest validate.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    url: str
    sha256: str
    size: int
    filename: str


@dataclass(frozen=True)
class Result:
    filename: str
    status: str
    size: int
    sha256: str
    attempts: int
    seconds: float


def digest(path: Path) -> tuple[str, int]:
    hasher = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
            size += len(chunk)
    return hasher.hexdigest(), size


def parse_manifest(path: Path) -> list[Entry]:
    by_name: dict[str, Entry] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 3:
            raise ValueError(f"{path}:{number}: expected URL, SHA-256, and size")
        url, expected_hash, expected_size = fields
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"{path}:{number}: only absolute HTTPS URLs are allowed")
        filename = Path(urllib.parse.unquote(parsed.path)).name
        if not filename or filename in {".", ".."}:
            raise ValueError(f"{path}:{number}: URL has no safe filename")
        if len(expected_hash) != 64 or any(c not in "0123456789abcdef" for c in expected_hash):
            raise ValueError(f"{path}:{number}: invalid lowercase SHA-256")
        entry = Entry(url, expected_hash, int(expected_size), filename)
        prior = by_name.get(filename)
        if prior is not None and prior != entry:
            raise ValueError(f"{path}:{number}: conflicting metadata for {filename}")
        by_name[filename] = entry
    return sorted(by_name.values(), key=lambda item: item.filename)


def validate(path: Path, entry: Entry) -> bool:
    if not path.is_file() or path.stat().st_size != entry.size:
        return False
    actual_hash, actual_size = digest(path)
    return actual_size == entry.size and actual_hash == entry.sha256


def download(entry: Entry, destination: Path, retries: int, timeout: int) -> Result:
    final_path = destination / entry.filename
    started = time.monotonic()
    if validate(final_path, entry):
        return Result(entry.filename, "cached", entry.size, entry.sha256, 0, 0.0)
    if final_path.exists():
        final_path.unlink()
    part_path = destination / f"{entry.filename}.part"
    context = ssl.create_default_context()
    last_error: BaseException | None = None
    for attempt in range(1, retries + 2):
        try:
            request = urllib.request.Request(entry.url, headers={"User-Agent": "provtrust-offline/0.1"})
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                with part_path.open("wb") as output:
                    shutil.copyfileobj(response, output, length=1024 * 1024)
                    output.flush()
                    os.fsync(output.fileno())
            if not validate(part_path, entry):
                actual_hash, actual_size = digest(part_path)
                raise ValueError(
                    f"integrity mismatch for {entry.filename}: "
                    f"size={actual_size}, sha256={actual_hash}"
                )
            part_path.replace(final_path)
            return Result(
                entry.filename,
                "downloaded",
                entry.size,
                entry.sha256,
                attempt,
                round(time.monotonic() - started, 3),
            )
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = exc
            part_path.unlink(missing_ok=True)
            if attempt <= retries:
                time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"failed {entry.filename} after {retries + 1} attempts: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 32:
        parser.error("--workers must be between 1 and 32")
    args.destination.mkdir(parents=True, exist_ok=True)
    entries = parse_manifest(args.manifest)
    results: list[Result] = []
    failures: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(download, entry, args.destination, args.retries, args.timeout): entry
            for entry in entries
        }
        for future in concurrent.futures.as_completed(futures):
            entry = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"{result.status:10s} {result.filename}", flush=True)
            except BaseException as exc:  # report every independent transfer failure
                message = f"{entry.filename}: {exc}"
                failures.append(message)
                print(f"FAILED     {message}", file=sys.stderr, flush=True)
    report = {
        "schema_version": "1.0.0",
        "manifest": str(args.manifest.resolve()),
        "destination": str(args.destination.resolve()),
        "entry_count": len(entries),
        "total_bytes": sum(entry.size for entry in entries),
        "results": [asdict(item) for item in sorted(results, key=lambda item: item.filename)],
        "failures": sorted(failures),
    }
    report_path = args.report or args.destination / "download-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
