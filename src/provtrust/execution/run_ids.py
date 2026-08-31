"""Human-readable and collision-resistant run identifiers."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

SAFE = re.compile(r"[^a-zA-Z0-9_.-]+")


def create_run_id(stage: str, task: str, git_commit: str, *, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    clean_stage = SAFE.sub("-", stage).strip("-")
    clean_task = SAFE.sub("-", task).strip("-")
    if not clean_stage or not clean_task:
        raise ValueError("stage and task must contain safe characters")
    suffix = hashlib.sha256(
        f"{timestamp.isoformat()}|{clean_stage}|{clean_task}|{git_commit}".encode("utf-8")
    ).hexdigest()[:8]
    return f"{timestamp:%Y%m%dT%H%M%SZ}-{clean_stage}-{clean_task}-{git_commit[:8]}-{suffix}"
