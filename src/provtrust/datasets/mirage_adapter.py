"""Safety-gated MIRAGE result adapter.

This module never creates or publishes poison documents. It only reads an isolated
local manifest after checking explicit safety declarations.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml


class MirageManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    isolated: bool
    public_indexing_disabled: bool
    authorized_corpus: bool
    upstream_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    corpus_path: Path
    result_path: Path

    @model_validator(mode="after")
    def enforce_safety_boundary(self) -> MirageManifest:
        if not (self.isolated and self.public_indexing_disabled and self.authorized_corpus):
            raise ValueError("MIRAGE adapter requires an isolated, non-indexed, authorized corpus")
        if self.corpus_path.is_absolute() and not self.result_path.is_absolute():
            raise ValueError("MIRAGE paths must use the same absolute/relative convention")
        return self


def load_mirage_manifest(path: Path) -> MirageManifest:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return MirageManifest.model_validate(payload)
