"""Content-addressed manifests for externally collected source snapshots."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: str
    source_id: str
    canonical_url: str
    retrieved_at: str
    content_path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str
    license_or_terms: str
    redistribution_allowed: bool

    @model_validator(mode="after")
    def validate_url(self) -> SourceSnapshot:
        parsed = urlparse(self.canonical_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("real-source snapshots require a canonical HTTPS URL")
        return self

    def verify_local_content(self, root: Path) -> None:
        target = (root / self.content_path).resolve()
        if root.resolve() not in target.parents:
            raise ValueError("snapshot path escapes the configured root")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != self.sha256:
            raise ValueError(f"snapshot hash mismatch: {self.snapshot_id}")
