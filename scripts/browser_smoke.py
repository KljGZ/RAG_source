"""CPU-only Playwright smoke test for the loopback controlled web service."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from provtrust.execution.atomic_io import atomic_write_json

LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18080/source/fixture-001")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK:
        raise ValueError("browser smoke URL must be loopback HTTP")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-first-run",
            ],
        )
        try:
            page = browser.new_page()
            response = page.goto(args.url, wait_until="networkidle", timeout=30_000)
            if response is None:
                raise RuntimeError("browser navigation produced no response")
            body = page.locator("body").inner_text()
            headers = response.headers
            passed = (
                response.status == 200
                and "harmless deployment fixture" in body
                and headers.get("x-robots-tag", "").startswith("noindex")
                and headers.get("cache-control") == "no-store"
            )
            report = {
                "schema_version": "1.0.0",
                "captured_at": datetime.now(UTC).isoformat(),
                "passed": passed,
                "url": args.url,
                "status": response.status,
                "title": page.title(),
                "chromium_version": browser.version,
                "launch_args": ["--disable-gpu", "--disable-dev-shm-usage", "--no-first-run"],
                "gpu_allocation_requested": False,
                "headers": {
                    "x-robots-tag": headers.get("x-robots-tag"),
                    "cache-control": headers.get("cache-control"),
                    "content-security-policy": headers.get("content-security-policy"),
                },
            }
        finally:
            browser.close()
    atomic_write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
