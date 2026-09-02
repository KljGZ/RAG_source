from __future__ import annotations

from scripts.validate_static_preflight import _optional_dict


def test_optional_score_metadata_preserves_objects() -> None:
    assert _optional_dict({"parse_success": True}) == {"parse_success": True}


def test_optional_score_metadata_turns_missing_or_invalid_values_into_empty_objects() -> None:
    assert _optional_dict(None) == {}
    assert _optional_dict("not-an-object") == {}
