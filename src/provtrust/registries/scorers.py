"""Typed scorer-function registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from provtrust.registries.base import Registry

ScorerFunction = Callable[..., dict[str, float | int | bool | None]]


class ScorerRegistry(Registry[ScorerFunction]):
    def score(self, name: str, *args: Any, **kwargs: Any) -> dict[str, float | int | bool | None]:
        return self.get(name)(*args, **kwargs)
