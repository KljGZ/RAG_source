from __future__ import annotations

import pytest

from provtrust.tasks.l2d_replication import parse_numeric


@pytest.mark.parametrize(
    ("text", "expected"),
    [("42", 42.0), ("1,234.5", 1234.5), ("-2e-3", -0.002), ("25%", 0.25)],
)
def test_l2d_numeric_parser(text: str, expected: float) -> None:
    assert parse_numeric(text) == pytest.approx(expected)


def test_l2d_numeric_parser_rejects_explanations() -> None:
    with pytest.raises(ValueError, match="one numeric"):
        parse_numeric("The answer is 42")
