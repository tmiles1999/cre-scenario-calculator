"""Implied-price and down-payment scenario builders."""

import math

import pytest

from cre_calcs.model import CapRateSweep, DownPaymentSweep, LoanRateTerms
from cre_calcs.scenarios import (
    build_cap_implied_price_scenarios,
    build_down_payment_scenarios,
)


def test_implied_price_inverse_of_cap() -> None:
    noi = 700_000.0
    rates = LoanRateTerms(0.06, 30, 10)
    sweep = CapRateSweep(0.07, 0.005, 0, 0)
    rows = build_cap_implied_price_scenarios(
        operating_income=noi,
        down_payment_fraction=0.25,
        loan_rates=rates,
        cap_sweep=sweep,
    )
    r = rows[0]
    assert r.assumed_cap_rate == 0.07
    assert math.isclose(r.implied_purchase_price or 0.0, noi / 0.07, rel_tol=1e-9)
    assert math.isclose(r.loan_to_value, 0.75, rel_tol=1e-9)
    assert r.effective_down_payment_fraction == 0.25
    assert math.isclose(r.purchase_price, noi / 0.07, rel_tol=1e-9)
    assert math.isclose(
        r.purchase_price * (r.effective_down_payment_fraction or 0),
        (noi / 0.07) * 0.25,
        rel_tol=1e-6,
    )


def test_down_payment_sweep_changes_ltv() -> None:
    rates = LoanRateTerms(0.06, 30, 10)
    sweep = DownPaymentSweep(0.25, 0.05, 1, 1)
    rows = build_down_payment_scenarios(
        purchase_price=1_000_000.0,
        operating_income=80_000.0,
        listing_cap_for_display=0.08,
        loan_rates=rates,
        sweep=sweep,
    )
    ltvs = [r.loan_to_value for r in rows]
    assert min(ltvs) < max(ltvs)
