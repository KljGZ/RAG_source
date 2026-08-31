"""Exact/Monte-Carlo paired sign-flip randomization test."""

from __future__ import annotations

import itertools
from pydantic import BaseModel, ConfigDict
import numpy as np


class RandomizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observed_mean: float
    p_value_two_sided: float
    permutations: int
    exact: bool


def sign_flip_randomization_test(
    effects: tuple[float, ...], *, seed: int = 0, max_exact_clusters: int = 18, draws: int = 100_000
) -> RandomizationResult:
    if not effects:
        raise ValueError("randomization test requires paired effects")
    values = np.asarray(effects, dtype=float)
    observed = abs(float(np.mean(values)))
    if len(values) <= max_exact_clusters:
        means = [
            abs(float(np.mean(values * np.asarray(signs))))
            for signs in itertools.product((-1.0, 1.0), repeat=len(values))
        ]
        exact = True
    else:
        generator = np.random.default_rng(seed)
        signs = generator.choice((-1.0, 1.0), size=(draws, len(values)))
        means = np.abs(np.mean(signs * values, axis=1)).tolist()
        exact = False
    exceed = sum(value >= observed - 1e-15 for value in means)
    p_value = exceed / len(means) if exact else (exceed + 1) / (len(means) + 1)
    return RandomizationResult(
        observed_mean=float(np.mean(values)),
        p_value_two_sided=float(p_value),
        permutations=len(means),
        exact=exact,
    )
