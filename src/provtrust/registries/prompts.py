"""Prompt registry requiring frozen content hashes."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from provtrust.registries.base import Registry


class PromptEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    purpose: str
    version: str

    def read_verified(self) -> str:
        content = self.path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != self.sha256:
            raise ValueError(f"prompt hash mismatch: {self.path}")
        return content.decode("utf-8")


class PromptRegistry(Registry[PromptEntry]):
    pass
