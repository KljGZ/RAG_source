"""Deterministic lexical search over an offline controlled corpus."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from inspect_ai.tool import Tool, tool
from pydantic import BaseModel, ConfigDict, Field

from provtrust.datasets.io import read_jsonl

TOKEN = re.compile(r"[\w-]+", re.UNICODE)


class SearchDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    title: str
    source_id: str
    controlled_url: str
    text: str
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance_root_id: str
    condition: str


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rank: int
    document_id: str
    title: str
    source_id: str
    controlled_url: str
    score: float
    snippet: str
    provenance_root_id: str


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).casefold() for match in TOKEN.finditer(text))


class ControlledSearchIndex:
    def __init__(self, documents: tuple[SearchDocument, ...]) -> None:
        if len({document.document_id for document in documents}) != len(documents):
            raise ValueError("search document identifiers must be unique")
        self.documents = documents
        self._tokens = {document.document_id: Counter(_tokens(document.text)) for document in documents}
        self._document_frequency: Counter[str] = Counter()
        for counts in self._tokens.values():
            self._document_frequency.update(counts.keys())

    @classmethod
    def from_jsonl(cls, path: Path) -> ControlledSearchIndex:
        return cls(tuple(SearchDocument.model_validate(row) for row in read_jsonl(path)))

    def search(self, query: str, *, limit: int = 5) -> tuple[SearchHit, ...]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not 1 <= limit <= 20:
            raise ValueError("search limit must be within [1, 20]")
        query_terms = Counter(_tokens(query))
        scored: list[tuple[float, SearchDocument]] = []
        population = max(len(self.documents), 1)
        for document in self.documents:
            counts = self._tokens[document.document_id]
            length = max(sum(counts.values()), 1)
            score = 0.0
            for term, query_count in query_terms.items():
                inverse_document_frequency = math.log(
                    1.0 + population / (1.0 + self._document_frequency[term])
                )
                score += query_count * counts[term] / length * inverse_document_frequency
            if score > 0.0:
                scored.append((score, document))
        scored.sort(key=lambda value: (-value[0], value[1].document_id))
        hits: list[SearchHit] = []
        for rank, (score, document) in enumerate(scored[:limit], start=1):
            hits.append(
                SearchHit(
                    rank=rank,
                    document_id=document.document_id,
                    title=document.title,
                    source_id=document.source_id,
                    controlled_url=document.controlled_url,
                    score=score,
                    snippet=document.text[:280],
                    provenance_root_id=document.provenance_root_id,
                )
            )
        return tuple(hits)


@tool(parallel=True)
def controlled_search(index_path: str) -> Tool:
    """Create an Inspect tool backed by one immutable JSONL index."""

    index = ControlledSearchIndex.from_jsonl(Path(index_path))

    async def execute(query: str, limit: int = 5) -> str:
        """Search the isolated experiment corpus.

        Args:
            query: Search terms for the controlled corpus.
            limit: Maximum number of results, from one through twenty.

        Returns:
            Ranked JSON search results including provenance-root identifiers.
        """

        return json.dumps(
            [hit.model_dump(mode="json") for hit in index.search(query, limit=limit)],
            ensure_ascii=False,
        )

    return execute
