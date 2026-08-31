"""Small deterministic registry primitive."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    def __init__(self, entries: Iterable[tuple[str, T]] = ()) -> None:
        self._entries: dict[str, T] = {}
        for name, entry in entries:
            self.register(name, entry)

    def register(self, name: str, entry: T) -> None:
        if not name or name != name.strip():
            raise ValueError("registry name must be non-empty and trimmed")
        if name in self._entries:
            raise KeyError(f"duplicate registry entry: {name}")
        self._entries[name] = entry

    def get(self, name: str) -> T:
        try:
            return self._entries[name]
        except KeyError as error:
            raise KeyError(f"unknown registry entry: {name}") from error

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))

    def items(self) -> tuple[tuple[str, T], ...]:
        return tuple((name, self._entries[name]) for name in sorted(self._entries))
