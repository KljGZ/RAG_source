"""SQLite checkpoint store with explicit state transitions."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path


class ItemState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


ALLOWED_TRANSITIONS = {
    ItemState.PENDING: {ItemState.RUNNING, ItemState.SKIPPED},
    ItemState.RUNNING: {ItemState.SUCCEEDED, ItemState.FAILED, ItemState.PENDING},
    ItemState.FAILED: {ItemState.RUNNING, ItemState.SKIPPED},
    ItemState.SUCCEEDED: set(),
    ItemState.SKIPPED: set(),
}


class CheckpointStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self._connect() as connection:
            connection.execute("pragma journal_mode=wal")
            connection.execute(
                """
                create table if not exists items (
                  item_id text primary key,
                  state text not null,
                  attempts integer not null default 0,
                  updated_at text not null,
                  error_type text,
                  output_path text
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("pragma busy_timeout=30000")
        return connection

    def initialize(self, item_ids: tuple[str, ...]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.executemany(
                "insert or ignore into items(item_id,state,updated_at) values(?,?,?)",
                ((item_id, ItemState.PENDING.value, now) for item_id in item_ids),
            )

    def state(self, item_id: str) -> ItemState:
        with self._connect() as connection:
            row = connection.execute("select state from items where item_id=?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(item_id)
        return ItemState(row[0])

    def transition(
        self,
        item_id: str,
        target: ItemState,
        *,
        error_type: str | None = None,
        output_path: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute("begin immediate")
            row = connection.execute(
                "select state,attempts from items where item_id=?", (item_id,)
            ).fetchone()
            if row is None:
                raise KeyError(item_id)
            current = ItemState(row[0])
            if target not in ALLOWED_TRANSITIONS[current]:
                raise ValueError(f"illegal checkpoint transition: {current} -> {target}")
            attempts = int(row[1]) + (1 if target is ItemState.RUNNING else 0)
            connection.execute(
                "update items set state=?,attempts=?,updated_at=?,error_type=?,output_path=? where item_id=?",
                (target.value, attempts, now, error_type, output_path, item_id),
            )

    def counts(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute("select state,count(*) from items group by state").fetchall()
        return {str(state): int(count) for state, count in rows}

    def recover_stale_running(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "update items set state=?,updated_at=? where state=?",
                (
                    ItemState.PENDING.value,
                    datetime.now(timezone.utc).isoformat(),
                    ItemState.RUNNING.value,
                ),
            )
        return cursor.rowcount
