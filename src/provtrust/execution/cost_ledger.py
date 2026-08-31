"""Transactional token/API cost ledger and hard budget gate."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class BudgetExceeded(RuntimeError):
    pass


class CostLedger:
    def __init__(self, path: Path, *, budget_usd: float) -> None:
        if budget_usd < 0.0:
            raise ValueError("budget must be non-negative")
        self.path = path
        self.budget_usd = budget_usd
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("pragma journal_mode=wal")
            connection.execute(
                """
                create table if not exists costs (
                  id integer primary key,
                  run_id text not null,
                  item_id text not null,
                  provider text not null,
                  model text not null,
                  input_tokens integer not null,
                  output_tokens integer not null,
                  cost_usd real not null,
                  created_at text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30)

    def total(self) -> float:
        with self._connect() as connection:
            row = connection.execute("select coalesce(sum(cost_usd),0.0) from costs").fetchone()
        return float(row[0])

    def reserve_and_record(
        self,
        *,
        run_id: str,
        item_id: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        if min(input_tokens, output_tokens) < 0 or cost_usd < 0.0:
            raise ValueError("cost-ledger values must be non-negative")
        with self._connect() as connection:
            connection.execute("begin immediate")
            current = float(
                connection.execute("select coalesce(sum(cost_usd),0.0) from costs").fetchone()[0]
            )
            if current + cost_usd > self.budget_usd:
                raise BudgetExceeded(
                    f"cost {current + cost_usd:.6f} would exceed budget {self.budget_usd:.6f}"
                )
            connection.execute(
                "insert into costs(run_id,item_id,provider,model,input_tokens,output_tokens,cost_usd,created_at) values(?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    item_id,
                    provider,
                    model,
                    input_tokens,
                    output_tokens,
                    cost_usd,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
