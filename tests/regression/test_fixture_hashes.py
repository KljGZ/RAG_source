from __future__ import annotations

import hashlib
import json
from pathlib import Path


def test_snapshot_name_is_content_hash() -> None:
    index = json.loads(Path("web_env/search_index/documents.jsonl").read_text(encoding="utf-8"))
    snapshot = Path("web_env/source_snapshots") / f"{index['snapshot_hash']}.txt"
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == index["snapshot_hash"]


def test_frozen_prompt_hashes() -> None:
    manifest = json.loads(Path("prompts/frozen/MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["prompts"]:
        assert hashlib.sha256(Path(entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
