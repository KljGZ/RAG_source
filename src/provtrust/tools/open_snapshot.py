"""Open content-addressed snapshots inside an allowlisted root."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from inspect_ai.tool import Tool, tool

from provtrust.tools.controlled_search import ControlledSearchIndex, SearchDocument
from provtrust.tools.tool_policy import ToolPolicy


class SnapshotStore:
    def __init__(
        self,
        root: Path,
        policy: ToolPolicy,
        documents: tuple[SearchDocument, ...] = (),
    ) -> None:
        self.root = root.resolve()
        self.policy = policy
        self.documents = {document.document_id: document for document in documents}

    def open(self, relative_path: str, expected_sha256: str | None = None) -> dict[str, str]:
        path = self.policy.check_path(self.root / relative_path)
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if expected_sha256 is not None and digest != expected_sha256:
            raise ValueError("snapshot digest does not match the manifest")
        return {
            "relative_path": relative_path,
            "sha256": digest,
            "text": content.decode("utf-8"),
        }

    def open_document(
        self, document_id: str, expected_sha256: str | None = None
    ) -> dict[str, str | tuple[str, ...] | None]:
        document = self.documents.get(document_id)
        if document is None:
            raise KeyError(f"unknown controlled document: {document_id}")
        relative_path = document.snapshot_path or f"{document.snapshot_hash}.txt"
        expected = expected_sha256 or document.snapshot_hash
        opened = self.open(relative_path, expected)
        return {
            "document_id": document.document_id,
            "title": document.title,
            "source_id": document.source_id,
            "controlled_url": document.controlled_url,
            "relative_path": opened["relative_path"],
            "sha256": opened["sha256"],
            "published_at": document.published_at,
            "identifier": document.identifier,
            "claimed_source_id": document.claimed_source_id,
            "document_role": document.document_role,
            "provenance_root_id": document.provenance_root_id,
            "evidence_ids": document.evidence_ids,
            "text": opened["text"],
        }


@tool(parallel=True)
def open_snapshot(
    index_path: str, store_root: str, max_read_bytes: int = 1_000_000
) -> Tool:
    """Create a loopback/offline snapshot-opening tool."""

    root = Path(store_root).resolve()
    documents = ControlledSearchIndex.from_jsonl(Path(index_path)).documents
    store = SnapshotStore(
        root,
        ToolPolicy(allowed_file_roots=(root,), max_read_bytes=max_read_bytes),
        documents,
    )

    async def execute(document_id: str, expected_sha256: str | None = None) -> str:
        """Read an immutable controlled source snapshot.

        Args:
            document_id: Exact document identifier returned by controlled_search.
            expected_sha256: Optional expected lowercase SHA-256 digest.

        Returns:
            JSON containing content and its computed digest.
        """

        return json.dumps(
            store.open_document(document_id, expected_sha256), ensure_ascii=False
        )

    return execute
