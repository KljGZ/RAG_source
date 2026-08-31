"""Family-cluster bootstrap confidence intervals."""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict


class ClusterBootstrapResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    estimate: float
    lower: float
    upper: float
    confidence: float
    replicates: int
    cluster_count: int


def cluster_bootstrap_mean(
    cluster_values: dict[str, tuple[float, ...]],
    *,
    seed: int,
    replicates: int = 2_000,
    confidence: float = 0.95,
) -> ClusterBootstrapResult:
    if not cluster_values:
        raise ValueError("cluster bootstrap requires at least one cluster")
    if replicates < 100:
        raise ValueError("at least 100 bootstrap replicates are required")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be within (0, 1)")
    names = sorted(cluster_values)
    cluster_means = np.asarray(
        [float(np.mean(cluster_values[name])) for name in names], dtype=float
    )
    generator = np.random.default_rng(seed)
    samples = generator.choice(cluster_means, size=(replicates, len(names)), replace=True)
    replicate_means = np.mean(samples, axis=1)
    alpha = (1.0 - confidence) / 2.0
    lower, upper = np.quantile(replicate_means, [alpha, 1.0 - alpha])
    return ClusterBootstrapResult(
        estimate=float(np.mean(cluster_means)),
        lower=float(lower),
        upper=float(upper),
        confidence=confidence,
        replicates=replicates,
        cluster_count=len(names),
    )
