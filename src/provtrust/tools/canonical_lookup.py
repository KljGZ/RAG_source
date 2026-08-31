"""Resolve displayed source identities against an immutable local registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from inspect_ai.tool import Tool, tool


class CanonicalRegistry:
    def __init__(self, records: tuple[dict[str, Any], ...]) -> None:
        self.records = records

    @classmethod
    def from_json(cls, path: Path) -> CanonicalRegistry:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
            raise ValueError("canonical registry must be a JSON array of objects")
        return cls(tuple(value))

    def lookup(self, query: str) -> tuple[dict[str, Any], ...]:
        normalized = query.casefold().strip()
        matches: list[dict[str, Any]] = []
        for record in self.records:
            names = {str(record.get("source_id", "")), str(record.get("canonical_name", ""))}
            names.update(str(name) for name in record.get("aliases", []))
            if normalized in {name.casefold().strip() for name in names}:
                matches.append(record)
        return tuple(matches)


@tool(parallel=True)
def canonical_lookup(registry_path: str) -> Tool:
    registry = CanonicalRegistry.from_json(Path(registry_path))

    async def execute(source_name_or_id: str) -> str:
        """Resolve a source label to canonical controlled-registry entries.

        Args:
            source_name_or_id: Displayed source name, alias, or source identifier.

        Returns:
            JSON array of matching canonical source records.
        """

        return json.dumps(registry.lookup(source_name_or_id), ensure_ascii=False)

    return execute
