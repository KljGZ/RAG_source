"""Map validated claim-evidence relations to evidence-permission weights."""

from __future__ import annotations

from provtrust.schemas.evidence import Evidence, WarrantLevel

WARRANT_WEIGHT = {
    WarrantLevel.CONTRADICTION: -1.0,
    WarrantLevel.UNSUPPORTED: 0.0,
    WarrantLevel.RELATED_ONLY: 0.15,
    WarrantLevel.PARTIAL_SUPPORT: 0.55,
    WarrantLevel.DIRECT_SUPPORT: 1.0,
}


def warrant_weight(evidence: Evidence) -> float:
    return WARRANT_WEIGHT[evidence.warrant_level]


def evidence_permits_claim(evidence: Evidence, *, threshold: float = 0.5) -> bool:
    return warrant_weight(evidence) >= threshold
