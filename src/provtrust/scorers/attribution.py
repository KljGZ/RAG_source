"""Attribution- and identity-authenticity contrasts."""

from __future__ import annotations


def attribution_authenticity_gap(authentic_adoption: float, spoofed_adoption: float) -> float:
    """Positive values indicate greater adoption under authentic attribution."""

    return authentic_adoption - spoofed_adoption


def attribution_monotonicity_satisfied(authentic_adoption: float, spoofed_adoption: float) -> bool:
    return authentic_adoption >= spoofed_adoption


def identity_authenticity_gap(authentic_identity: float, spoofed_identity: float) -> float:
    return authentic_identity - spoofed_identity
