"""Content-addressed dataset registry."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from provtrust.registries.base import Registry


class DatasetEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_version: str
    split: str
    license_id: str
    source_revision: str | None = None


class DatasetRegistry(Registry[DatasetEntry]):
    pass
