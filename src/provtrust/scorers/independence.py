"""Provenance-root and consensus-laundering estimands."""

from __future__ import annotations


def consensus_laundering_amplification(dependent_duplicates: float, single_root: float) -> float:
    """Extra adoption caused by apparent count with no new root."""

    return dependent_duplicates - single_root


def independent_evidence_gain(independent_roots: float, single_root: float) -> float:
    return independent_roots - single_root


def root_normalized_adoption(adoption: float, effective_root_count: int) -> float:
    if effective_root_count < 1:
        raise ValueError("effective root count must be positive")
    return adoption / effective_root_count
