"""Minimal publication plots with explicit uncertainty intervals."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


def effect_interval_plot(
    labels: tuple[str, ...],
    estimates: tuple[float, ...],
    lower: tuple[float, ...],
    upper: tuple[float, ...],
    output: Path,
) -> None:
    if not (len(labels) == len(estimates) == len(lower) == len(upper)):
        raise ValueError("plot vectors must have equal length")
    figure, axis = plt.subplots(figsize=(7, max(3, 0.4 * len(labels))))
    positions = list(range(len(labels)))
    errors = [
        [estimate - low for estimate, low in zip(estimates, lower)],
        [high - estimate for estimate, high in zip(estimates, upper)],
    ]
    axis.errorbar(estimates, positions, xerr=errors, fmt="o", capsize=3)
    axis.axvline(0.0, color="black", linewidth=0.8)
    axis.set_yticks(positions, labels)
    axis.set_xlabel("Effect estimate (interval)")
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=200)
    plt.close(figure)
