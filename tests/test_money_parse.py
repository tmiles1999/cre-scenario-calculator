"""Tests for money amount parsing."""

import math
import pytest

from cre_calcs.money_parse import parse_money_amount


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2.7M", 2_700_000.0),
        ("2.7m", 2_700_000.0),
        ("874k", 874_000.0),
        ("874K", 874_000.0),
        ("1M", 1_000_000.0),
        ("250k", 250_000.0),
        ("2700000", 2_700_000.0),
        ("$2,700,000", 2_700_000.0),
        ("$ 2.7 M", 2_700_000.0),
        ("  874 k  ", 874_000.0),
        ("0.5m", 500_000.0),
    ],
)
def test_parse_money_amount_examples(text: str, expected: float) -> None:
    assert math.isclose(parse_money_amount(text), expected, rel_tol=0.0, abs_tol=0.0)


def test_parse_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_money_amount("   ")


def test_parse_rejects_suffix_only() -> None:
    with pytest.raises(ValueError, match="invalid"):
        parse_money_amount("M")


def test_parse_rejects_bad_number() -> None:
    with pytest.raises(ValueError, match="invalid number"):
        parse_money_amount("12.34.56k")
