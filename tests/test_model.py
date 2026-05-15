"""Validation rules on domain models."""

import pytest

from cre_calcs.model import CapRateSweep, Listing, LoanTerms


def test_listing_rejects_non_positive_price() -> None:
    with pytest.raises(ValueError, match="purchase_price"):
        Listing(purchase_price=0, listing_cap_rate=0.06)


def test_cap_sweep_rejects_non_positive_step() -> None:
    with pytest.raises(ValueError, match="step"):
        CapRateSweep(0.06, 0.0, 1, 1)


def test_cap_sweep_drops_non_positive_bands() -> None:
    """Wide step pushes grid below zero; only valid caps remain."""
    sweep = CapRateSweep(0.068, 0.1, 8, 8)
    caps = sweep.cap_rates_low_to_high()
    assert all(c > 0 for c in caps)
    assert len(caps) < 1 + sweep.steps_below + sweep.steps_above
    assert any(abs(c - 0.068) < 1e-9 for c in caps)

