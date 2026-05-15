"""Parse human-friendly dollar amounts (e.g. 2.7M, 874k)."""

from __future__ import annotations

import re

_SUFFIX_MULTIPLIER: dict[str, float] = {
    "k": 1_000.0,
    "m": 1_000_000.0,
    "b": 1_000_000_000.0,
}


def parse_money_amount(value: str) -> float:
    """Parse a dollar amount from a string.

    Accepts plain numbers, optional ``$`` and commas, optional ``k`` / ``m`` / ``b``
    suffix (case-insensitive). All whitespace is ignored.

    Examples: ``"2.7M"``, ``"874k"``, ``"$2,700,000"``, ``"2700000"``.
    """
    collapsed = re.sub(r"\s+", "", value.strip()).replace("$", "").replace(",", "")
    if not collapsed:
        raise ValueError("amount is empty")

    lowered = collapsed.lower()
    last = lowered[-1]
    if last in _SUFFIX_MULTIPLIER:
        num_part = lowered[:-1]
        if not num_part:
            raise ValueError(f"invalid amount: {value!r}")
        mult = _SUFFIX_MULTIPLIER[last]
    else:
        num_part = lowered
        mult = 1.0

    try:
        return float(num_part) * mult
    except ValueError as e:
        raise ValueError(f"invalid number in amount: {value!r}") from e
