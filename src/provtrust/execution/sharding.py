"""Stable, order-independent item sharding."""

from __future__ import annotations

import hashlib


def shard_for_item(item_id: str, shard_count: int, *, seed: int = 0) -> int:
    if shard_count < 1:
        raise ValueError("shard count must be positive")
    digest = hashlib.sha256(f"{seed}:{item_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % shard_count


def select_shard(item_ids: tuple[str, ...], shard_index: int, shard_count: int) -> tuple[str, ...]:
    if not 0 <= shard_index < shard_count:
        raise ValueError("invalid shard index")
    return tuple(
        item_id for item_id in item_ids if shard_for_item(item_id, shard_count) == shard_index
    )
