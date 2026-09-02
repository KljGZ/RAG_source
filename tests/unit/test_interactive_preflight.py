from __future__ import annotations

from scripts.validate_interactive_preflight import _revision_matches


def test_revision_match_accepts_unambiguous_short_or_full_form() -> None:
    full = "83a215813d88e4d3f97c79dde0a81d9d4e0613cf"

    assert _revision_matches("83a2158", full)
    assert _revision_matches(full, "83a2158")
    assert not _revision_matches("83a2159", full)
    assert not _revision_matches("83a", full)
