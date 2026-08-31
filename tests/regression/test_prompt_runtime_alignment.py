from __future__ import annotations

from pathlib import Path

from provtrust.tasks.common import SYSTEM_PROMPT


def test_runtime_answer_prompt_matches_frozen_prompt() -> None:
    frozen = Path("prompts/frozen/answer-system-v0.txt").read_text(encoding="utf-8")
    assert SYSTEM_PROMPT == frozen
