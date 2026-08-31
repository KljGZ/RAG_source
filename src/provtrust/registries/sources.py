"""Canonical source registry."""

from __future__ import annotations

from provtrust.registries.base import Registry
from provtrust.schemas.source import SourceEntity


class SourceRegistry(Registry[SourceEntity]):
    def resolve_displayed_name(self, displayed_name: str) -> tuple[SourceEntity, ...]:
        normalized = displayed_name.casefold().strip()
        return tuple(
            source
            for _, source in self.items()
            if source.displayed_name.casefold().strip() == normalized
        )
