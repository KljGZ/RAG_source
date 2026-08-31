"""Inspect AI task registrations for every experimental track."""

from provtrust.tasks.attribution_authenticity import attribution_authenticity
from provtrust.tasks.consensus_laundering import consensus_laundering
from provtrust.tasks.evidence_warrant import evidence_warrant
from provtrust.tasks.interactive_verification import interactive_verification
from provtrust.tasks.l2d_replication import l2d_replication
from provtrust.tasks.mirage_stress import mirage_stress
from provtrust.tasks.pavg_defense import pavg_defense
from provtrust.tasks.rationale_faithfulness import rationale_faithfulness
from provtrust.tasks.static_factorial import static_factorial

__all__ = [
    "attribution_authenticity",
    "consensus_laundering",
    "evidence_warrant",
    "interactive_verification",
    "l2d_replication",
    "mirage_stress",
    "pavg_defense",
    "rationale_faithfulness",
    "static_factorial",
]
