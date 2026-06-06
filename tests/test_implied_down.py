"""Implied-price and down-payment scenario builders."""

import math

import pytest

from cre_calcs.model import CapRateSweep, DownPaymentSweep, LoanRateTerms
from cre_calcs.model import Listing, LoanTerms
from cre_calcs.scenarios import (
    build_cap_implied_price_scenarios,
    build_cap_rate_scenarios,
    build_down_payment_scenarios,
    inject_offer_cap_row,
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


def test_inject_offer_cap_row_inserts_implied_price_at_offer_cap() -> None:
    noi = 155_808.0
    list_price = 2_596_800.0
    offer_price = 2_300_000.0
    rates = LoanRateTerms(0.065, 25, 5)
    loan = rates.with_down_payment(0.25)
    sweep = CapRateSweep(0.06, 0.01, 2, 2)
    rows = build_cap_implied_price_scenarios(
        operating_income=noi,
        down_payment_fraction=0.25,
        loan_rates=rates,
        cap_sweep=sweep,
    )
    injected = inject_offer_cap_row(
        rows,
        operating_income=noi,
        offer_price=offer_price,
        list_price=list_price,
        loan=loan,
        implied_price_mode=True,
        down_payment_fraction=0.25,
    )
    assert len(injected) == len(rows) + 1
    offer_cap = noi / offer_price
    matches = [
        r
        for r in injected
        if r.assumed_cap_rate is not None
        and math.isclose(r.assumed_cap_rate, offer_cap, rel_tol=1e-9)
    ]
    assert len(matches) == 1
    assert math.isclose(matches[0].implied_purchase_price or 0.0, offer_price, rel_tol=1e-6)
    caps = [r.assumed_cap_rate for r in injected if r.assumed_cap_rate is not None]
    assert caps == sorted(caps)


def test_inject_offer_cap_row_skips_when_offer_within_one_percent_of_list() -> None:
    noi = 155_808.0
    list_price = 2_596_800.0
    offer_price = list_price * 1.005
    rates = LoanRateTerms(0.065, 25, 5)
    loan = rates.with_down_payment(0.25)
    sweep = CapRateSweep(0.06, 0.01, 0, 0)
    rows = build_cap_implied_price_scenarios(
        operating_income=noi,
        down_payment_fraction=0.25,
        loan_rates=rates,
        cap_sweep=sweep,
    )
    injected = inject_offer_cap_row(
        rows,
        operating_income=noi,
        offer_price=offer_price,
        list_price=list_price,
        loan=loan,
        implied_price_mode=True,
        down_payment_fraction=0.25,
    )
    assert injected == rows


def test_inject_offer_cap_row_fixed_price_mode_uses_stated_noi() -> None:
    noi = 155_808.0
    list_price = 2_596_800.0
    offer_price = 2_300_000.0
    listing = Listing(purchase_price=offer_price, listing_cap_rate=0.06)
    loan = LoanTerms(0.25, 0.065, 25, 5)
    sweep = CapRateSweep(0.06, 0.01, 2, 2)
    rows = build_cap_rate_scenarios(listing, loan, sweep)
    injected = inject_offer_cap_row(
        rows,
        operating_income=noi,
        offer_price=offer_price,
        list_price=list_price,
        loan=loan,
        implied_price_mode=False,
    )
    offer_cap = noi / offer_price
    matches = [
        r
        for r in injected
        if r.assumed_cap_rate is not None
        and math.isclose(r.assumed_cap_rate, offer_cap, rel_tol=1e-9)
    ]
    assert len(matches) == 1
    assert math.isclose(matches[0].net_operating_income, noi, rel_tol=1e-6)
    assert math.isclose(matches[0].purchase_price, offer_price, rel_tol=1e-6)


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
