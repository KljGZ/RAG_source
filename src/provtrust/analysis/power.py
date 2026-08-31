"""Simulation-based clustered power planning; never infer sample size from pilot p-values."""

from __future__ import annotations

import numpy as np


def simulated_paired_power(
    *,
    family_count: int,
    standardized_effect: float,
    within_family_sd: float = 1.0,
    alpha: float = 0.05,
    simulations: int = 5_000,
    seed: int = 0,
) -> float:
    if family_count < 2 or simulations < 100:
        raise ValueError("power simulation requires families and at least 100 simulations")
    if within_family_sd <= 0.0 or not 0.0 < alpha < 1.0:
        raise ValueError("invalid power parameters")
    generator = np.random.default_rng(seed)
    effects = generator.normal(
        loc=standardized_effect * within_family_sd,
        scale=within_family_sd,
        size=(simulations, family_count),
    )
    means = np.mean(effects, axis=1)
    standard_errors = np.std(effects, axis=1, ddof=1) / np.sqrt(family_count)
    z_statistics = np.divide(means, standard_errors, out=np.zeros_like(means), where=standard_errors > 0)
    critical = 1.959963984540054
    return float(np.mean(np.abs(z_statistics) > critical))
