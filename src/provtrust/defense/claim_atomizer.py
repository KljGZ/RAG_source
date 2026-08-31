"""Deterministic claim atomization baseline.

It is intentionally conservative and replaceable. LLM-generated atoms must be
human/deterministically validated before they can become benchmark gold labels.
"""

from __future__ import annotations

import re

BOUNDARY = re.compile(r"(?<=[.!?。！？])\s+")


def atomize_claims(text: str) -> tuple[str, ...]:
    atoms = tuple(segment.strip() for segment in BOUNDARY.split(text) if segment.strip())
    return atoms or ((text.strip(),) if text.strip() else ())
