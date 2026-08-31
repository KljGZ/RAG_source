"""Publication-table helpers that retain effect sizes and intervals."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def markdown_table(rows: Iterable[dict[str, Any]], columns: tuple[str, ...]) -> str:
    materialized = list(rows)
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |"
        for row in materialized
    ]
    return "\n".join([header, divider, *body]) + "\n"
