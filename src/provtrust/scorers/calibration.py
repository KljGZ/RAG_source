"""Calibration metrics with deterministic binning."""

from __future__ import annotations

import numpy as np


def brier_score(probabilities: tuple[float, ...], labels: tuple[bool, ...]) -> float:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must be non-empty and aligned")
    if any(not 0.0 <= value <= 1.0 for value in probabilities):
        raise ValueError("probabilities must be within [0, 1]")
    return float(np.mean([(probability - float(label)) ** 2 for probability, label in zip(probabilities, labels)]))


def expected_calibration_error(
    probabilities: tuple[float, ...], labels: tuple[bool, ...], *, bins: int = 10
) -> float:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must be non-empty and aligned")
    if bins < 1:
        raise ValueError("bins must be positive")
    probabilities_array = np.asarray(probabilities, dtype=float)
    labels_array = np.asarray(labels, dtype=float)
    if np.any((probabilities_array < 0.0) | (probabilities_array > 1.0)):
        raise ValueError("probabilities must be within [0, 1]")
    boundaries = np.linspace(0.0, 1.0, bins + 1)
    assignments = np.minimum(np.digitize(probabilities_array, boundaries[1:-1]), bins - 1)
    error = 0.0
    for index in range(bins):
        mask = assignments == index
        if not np.any(mask):
            continue
        weight = float(np.mean(mask))
        error += weight * abs(float(np.mean(probabilities_array[mask])) - float(np.mean(labels_array[mask])))
    return error
