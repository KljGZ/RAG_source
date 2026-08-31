"""Optional RAGChecker bridge with explicit availability reporting."""

from __future__ import annotations

import importlib.util
from typing import Any


def ragchecker_available() -> bool:
    return importlib.util.find_spec("ragchecker") is not None


def evaluate_with_ragchecker(*args: Any, **kwargs: Any) -> Any:
    if not ragchecker_available():
        raise RuntimeError("RAGChecker optional dependency is not installed")
    import ragchecker  # type: ignore[import-not-found]

    evaluator = getattr(ragchecker, "RAGResults", None)
    if evaluator is None:
        raise RuntimeError("installed RAGChecker API is unsupported; pin and add an adapter")
    return evaluator(*args, **kwargs)
