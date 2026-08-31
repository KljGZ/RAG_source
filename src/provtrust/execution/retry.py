"""Bounded retry policy that preserves every failed attempt."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    retryable_error_names: frozenset[str] = frozenset(
        {"RateLimitError", "TimeoutError", "ConnectionError", "ServiceUnavailableError"}
    )

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or self.base_delay_seconds < 0.0:
            raise ValueError("invalid retry policy")


@dataclass(frozen=True)
class FailedAttempt:
    attempt: int
    error_type: str
    message: str


@dataclass(frozen=True)
class RetryResult(Generic[T]):
    value: T
    failures: tuple[FailedAttempt, ...]


async def run_with_retry(operation: Callable[[], Awaitable[T]], policy: RetryPolicy) -> RetryResult[T]:
    failures: list[FailedAttempt] = []
    for attempt in range(policy.max_attempts):
        try:
            return RetryResult(await operation(), tuple(failures))
        except Exception as error:
            error_type = type(error).__name__
            failures.append(FailedAttempt(attempt, error_type, str(error)))
            retryable = error_type in policy.retryable_error_names
            if not retryable or attempt + 1 == policy.max_attempts:
                raise
            await asyncio.sleep(policy.base_delay_seconds * (2**attempt))
    raise AssertionError("unreachable retry state")
