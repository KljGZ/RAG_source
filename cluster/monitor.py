"""Thin executable wrapper for the installed project monitor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from provtrust.monitoring import Monitor, load_monitor_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    report = Monitor(load_monitor_config(args.config)).run_once()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if bool(report["healthy"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
