"""Open content-addressed snapshots inside an allowlisted root."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from inspect_ai.tool import Tool, tool

from provtrust.tools.tool_policy import ToolPolicy


class SnapshotStore:
    def __init__(self, root: Path, policy: ToolPolicy) -> None:
        self.root = root.resolve()
        self.policy = policy

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


@tool(parallel=True)
def open_snapshot(store_root: str, max_read_bytes: int = 1_000_000) -> Tool:
    """Create a loopback/offline snapshot-opening tool."""

    root = Path(store_root).resolve()
    store = SnapshotStore(root, ToolPolicy(allowed_file_roots=(root,), max_read_bytes=max_read_bytes))

    async def execute(relative_path: str, expected_sha256: str | None = None) -> str:
        """Read an immutable controlled source snapshot.

        Args:
            relative_path: Path relative to the configured snapshot root.
            expected_sha256: Optional expected lowercase SHA-256 digest.

        Returns:
            JSON containing content and its computed digest.
        """

        return json.dumps(store.open(relative_path, expected_sha256), ensure_ascii=False)

    return execute
