"""Verify identifiers against a frozen local registry, not model memory."""

from __future__ import annotations

import json
import re
from enum import StrEnum
from pathlib import Path
from typing import Any

from inspect_ai.tool import Tool, tool


class IdentifierType(StrEnum):
    DOI = "doi"
    PMID = "pmid"
    ANNOUNCEMENT = "announcement"
    REGULATION = "regulation"


PATTERNS = {
    IdentifierType.DOI: re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE),
    IdentifierType.PMID: re.compile(r"^\d{1,9}$"),
    IdentifierType.ANNOUNCEMENT: re.compile(r"^[A-Z][A-Z0-9-]{3,40}$"),
    IdentifierType.REGULATION: re.compile(r"^[A-Z0-9][A-Z0-9()./_-]{2,80}$"),
}


class IdentifierRegistry:
    def __init__(self, records: dict[str, dict[str, Any]]) -> None:
        self.records = records

    @classmethod
    def from_json(cls, path: Path) -> IdentifierRegistry:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not all(isinstance(v, dict) for v in value.values()):
            raise ValueError("identifier registry must map identifiers to records")
        return cls(value)

    def verify(self, identifier: str, kind: IdentifierType) -> dict[str, Any]:
        syntax_valid = bool(PATTERNS[kind].fullmatch(identifier.strip()))
        record = self.records.get(identifier)
        return {
            "identifier": identifier,
            "kind": kind,
            "syntax_valid": syntax_valid,
            "registry_match": record is not None,
            "record": record,
        }


@tool(parallel=True)
def verify_identifier(registry_path: str) -> Tool:
    registry = IdentifierRegistry.from_json(Path(registry_path))

    async def execute(identifier: str, kind: str) -> str:
        """Verify a citation or announcement identifier in the frozen registry.

        Args:
            identifier: Exact identifier string to verify.
            kind: One of doi, pmid, announcement, or regulation.

        Returns:
            JSON with syntax and registry-match results.
        """

        return json.dumps(registry.verify(identifier, IdentifierType(kind)), ensure_ascii=False)

    return execute
