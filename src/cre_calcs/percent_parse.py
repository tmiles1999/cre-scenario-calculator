"""Parse user-entered percentages into decimal rates (6.5%% -> 0.065)."""

from __future__ import annotations

import re


def parse_display_percent_to_decimal(value: str) -> float:
    """Convert a **display percentage** to a decimal rate on [0, 1) scale.

    The input is always treated as a percent number, **never** as a pre-scaled
    decimal: ``6.8`` → ``0.068``, ``0.1`` → ``0.001`` (0.1%%), ``6.25%`` → ``0.0625``.

    Whitespace is ignored; an optional trailing ``%`` is stripped.
    """
    collapsed = re.sub(r"\s+", "", value.strip())
    if not collapsed:
        raise ValueError("percentage is empty")
    if collapsed.endswith("%"):
        collapsed = collapsed[:-1]
    if not collapsed:
        raise ValueError("percentage is empty")
    return float(collapsed) / 100.0
