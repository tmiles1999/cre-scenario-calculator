"""Down payment sweep grid, sizing (LTV / principal / equity), and scenario rows."""

from __future__ import annotations

import math

import pytest

from cre_calcs.metrics import equity_invested, loan_amount, loan_to_value
from cre_calcs.model import DownPaymentSweep, Listing, LoanRateTerms, LoanTerms
from cre_calcs.mortgage import annual_debt_service
from cre_calcs.scenarios import build_down_payment_scenarios
from cre_calcs.table import scenario_rows_matrix


def test_loan_amount_and_equity_sum_to_purchase_price() -> None:
    listing = Listing(purchase_price=3_200_000.0, listing_cap_rate=0.06)
    loan = LoanTerms(
        down_payment_fraction=0.30,
        annual_interest_rate=0.0675,
        amortization_years=30,
        balloon_years=10,
    )
    assert math.isclose(
        loan_amount(listing, loan) + equity_invested(listing, loan),
        listing.purchase_price,
        rel_tol=1e-12,
    )
    assert math.isclose(loan_to_value(listing, loan), 0.70, rel_tol=1e-12)


def test_down_payment_sweep_includes_center_and_is_sorted() -> None:
    sweep = DownPaymentSweep(
        center_down_payment_fraction=0.25,
        step=0.05,
        steps_below=2,
        steps_above=2,
    )
    fracs = sweep.down_payment_fractions_low_to_high()
    assert 0.25 in fracs
    assert fracs == tuple(sorted(fracs))
    assert len(fracs) == 1 + sweep.steps_below + sweep.steps_above


def test_down_payment_sweep_clips_outside_zero_one() -> None:
    """Bands outside [0, 1] are dropped; center remains valid."""
    sweep = DownPaymentSweep(
        center_down_payment_fraction=0.10,
        step=0.05,
        steps_below=5,
        steps_above=20,
    )
    fracs = sweep.down_payment_fractions_low_to_high()
    assert all(0.0 <= f <= 1.0 for f in fracs)
    assert 0.10 in fracs
    assert min(fracs) >= 0.0
    assert max(fracs) <= 1.0
    assert len(fracs) < 1 + sweep.steps_below + sweep.steps_above


@pytest.mark.parametrize(
    ("down", "expected_ltv"),
    [(0.0, 1.0), (0.25, 0.75), (0.50, 0.50), (1.0, 0.0)],
)
def test_ltv_is_one_minus_down_payment_fraction(down: float, expected_ltv: float) -> None:
    listing = Listing(purchase_price=1_000_000.0, listing_cap_rate=0.065)
    loan = LoanTerms(
        down_payment_fraction=down,
        annual_interest_rate=0.06,
        amortization_years=30,
        balloon_years=10,
    )
    assert math.isclose(loan_to_value(listing, loan), expected_ltv, rel_tol=1e-12)


def test_down_payment_scenarios_ltv_and_effective_down_align() -> None:
    rates = LoanRateTerms(0.065, 30, 10)
    sweep = DownPaymentSweep(0.30, 0.10, 1, 1)
    rows = build_down_payment_scenarios(
        purchase_price=2_000_000.0,
        operating_income=150_000.0,
        listing_cap_for_display=0.075,
        loan_rates=rates,
        sweep=sweep,
    )
    assert len(rows) == len(sweep.down_payment_fractions_low_to_high())
    for r in rows:
        d = r.effective_down_payment_fraction
        assert d is not None
        assert math.isclose(r.loan_to_value, 1.0 - d, rel_tol=1e-9)
        assert math.isclose(r.net_operating_income, 150_000.0, rel_tol=1e-9)


def test_down_payment_scenarios_ads_falls_when_equity_rises() -> None:
    """Lower principal from a larger down payment reduces annual debt service."""
    rates = LoanRateTerms(0.06, 30, 10)
    sweep = DownPaymentSweep(0.25, 0.05, 2, 2)
    rows = build_down_payment_scenarios(
        purchase_price=1_000_000.0,
        operating_income=80_000.0,
        listing_cap_for_display=0.08,
        loan_rates=rates,
        sweep=sweep,
    )
    downs = [r.effective_down_payment_fraction for r in rows]
    adss = [r.annual_debt_service for r in rows]
    assert downs == sorted(downs)
    assert adss == sorted(adss, reverse=True)


def test_zero_down_cash_on_cash_is_nan() -> None:
    rates = LoanRateTerms(0.06, 30, 10)
    sweep = DownPaymentSweep(0.0, 0.05, 0, 1)
    rows = build_down_payment_scenarios(
        purchase_price=900_000.0,
        operating_income=60_000.0,
        listing_cap_for_display=0.067,
        loan_rates=rates,
        sweep=sweep,
    )
    r0 = rows[0]
    assert r0.effective_down_payment_fraction == 0.0
    assert math.isnan(r0.cash_on_cash)
    assert r0.debt_service_coverage_ratio is not None


def test_full_equity_no_debt_service_dscr_undefined() -> None:
    rates = LoanRateTerms(0.06, 30, 10)
    sweep = DownPaymentSweep(1.0, 0.05, 1, 0)
    rows = build_down_payment_scenarios(
        purchase_price=500_000.0,
        operating_income=40_000.0,
        listing_cap_for_display=0.08,
        loan_rates=rates,
        sweep=sweep,
    )
    r_full = rows[-1]
    assert r_full.effective_down_payment_fraction == 1.0
    assert math.isclose(r_full.annual_debt_service, 0.0, abs_tol=1e-6)
    assert r_full.debt_service_coverage_ratio is None
    assert math.isclose(
        r_full.cash_on_cash,
        r_full.net_operating_income / 500_000.0,
        rel_tol=1e-9,
    )


def test_principal_from_row_matches_loan_amount_formula() -> None:
    price = 1_250_000.0
    rates = LoanRateTerms(0.055, 25, 10)
    sweep = DownPaymentSweep(0.20, 0.05, 0, 2)
    rows = build_down_payment_scenarios(
        purchase_price=price,
        operating_income=95_000.0,
        listing_cap_for_display=0.076,
        loan_rates=rates,
        sweep=sweep,
    )
    listing = Listing(purchase_price=price, listing_cap_rate=0.076)
    for r in rows:
        d = r.effective_down_payment_fraction
        assert d is not None
        loan = rates.with_down_payment(d)
        principal = loan_amount(listing, loan)
        ads = annual_debt_service(
            principal=principal,
            annual_interest_rate=loan.annual_interest_rate,
            amortization_years=loan.amortization_years,
        )
        assert math.isclose(r.annual_debt_service, ads, rel_tol=1e-6)


def test_down_sweep_table_down_column_matches_price_times_equity_fraction() -> None:
    price = 2_000_000.0
    rates = LoanRateTerms(0.06, 30, 10)
    sweep = DownPaymentSweep(0.25, 0.05, 0, 1)
    rows = build_down_payment_scenarios(
        purchase_price=price,
        operating_income=100_000.0,
        listing_cap_for_display=0.08,
        loan_rates=rates,
        sweep=sweep,
    )
    headers, data = scenario_rows_matrix(rows)
    assert headers[0] == "Scenario (Down)"
    assert "Down ($)" in headers
    col = headers.index("Down ($)")
    for row, r in zip(data, rows, strict=True):
        d = r.effective_down_payment_fraction
        assert d is not None
        assert row[col] == f"${price * d:,.0f}"
        assert all(r2.purchase_price == price for r2 in rows)
