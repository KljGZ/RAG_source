"""Human/judge agreement with metrics robust to class imbalance."""

from __future__ import annotations

from sklearn.metrics import (  # type: ignore[import-untyped]
    cohen_kappa_score,
    f1_score,
    matthews_corrcoef,
)


def binary_agreement(reference: tuple[bool, ...], prediction: tuple[bool, ...]) -> dict[str, float]:
    if len(reference) != len(prediction) or not reference:
        raise ValueError("agreement labels must be non-empty and aligned")
    truth = [int(value) for value in reference]
    predicted = [int(value) for value in prediction]
    return {
        "cohen_kappa": float(cohen_kappa_score(truth, predicted)),
        "mcc": float(matthews_corrcoef(truth, predicted)),
        "f1": float(f1_score(truth, predicted, zero_division=0)),
        "accuracy": sum(left == right for left, right in zip(reference, prediction)) / len(reference),
    }
