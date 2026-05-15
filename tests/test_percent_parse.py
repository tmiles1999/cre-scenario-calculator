"""Tests for display-percentage parsing."""

import math
import pytest

from cre_calcs.percent_parse import parse_display_percent_to_decimal


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("6.8", 0.068),
        ("6.25%", 0.0625),
        ("0.1", 0.001),
        ("0.25", 0.0025),
        ("100", 1.0),
        ("  3  ", 0.03),
    ],
)
def test_parse_display_percent(text: str, expected: float) -> None:
    assert math.isclose(parse_display_percent_to_decimal(text), expected, rel_tol=0.0, abs_tol=1e-12)


def test_parse_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_display_percent_to_decimal("   ")


def test_old_decimal_style_is_not_special_cased() -> None:
    """0.065 means 0.065% per contract, not 6.5%."""
    assert math.isclose(parse_display_percent_to_decimal("0.065"), 0.00065, rel_tol=0.0, abs_tol=1e-15)
