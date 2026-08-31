"""Canonical source-entity resolution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from provtrust.registries.sources import SourceRegistry
from provtrust.schemas.source import SourceEntity


class SourceResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str
    matches: tuple[SourceEntity, ...]
    ambiguous: bool
    resolved_source_id: str | None


def resolve_source(query: str, registry: SourceRegistry) -> SourceResolution:
    try:
        direct = registry.get(query)
        matches = (direct,)
    except KeyError:
        matches = registry.resolve_displayed_name(query)
    return SourceResolution(
        query=query,
        matches=matches,
        ambiguous=len(matches) != 1,
        resolved_source_id=matches[0].source_id if len(matches) == 1 else None,
    )
