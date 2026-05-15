"""Scenario grid: sweep cap rates and compute underwriting metrics."""

import math

from cre_calcs.model import CapRateSweep, Listing, LoanTerms
from cre_calcs.mortgage import annual_debt_service
from cre_calcs.scenarios import build_cap_rate_scenarios


def test_scenario_row_count_matches_caps() -> None:
    listing = Listing(purchase_price=2_000_000.0, listing_cap_rate=0.06)
    loan = LoanTerms(
        down_payment_fraction=0.30,
        annual_interest_rate=0.065,
        amortization_years=25,
        balloon_years=7,
    )
    sweep = CapRateSweep(center_cap_rate=0.06, step=0.0025, steps_below=2, steps_above=2)
    rows = build_cap_rate_scenarios(listing, loan, sweep)
    assert len(rows) == 1 + sweep.steps_below + sweep.steps_above


def test_ltv_constant_across_cap_sweep() -> None:
    listing = Listing(purchase_price=5_000_000.0, listing_cap_rate=0.055)
    loan = LoanTerms(
        down_payment_fraction=0.25,
        annual_interest_rate=0.06,
        amortization_years=30,
        balloon_years=10,
    )
    sweep = CapRateSweep(0.055, 0.005, 1, 1)
    rows = build_cap_rate_scenarios(listing, loan, sweep)
    assert len({r.loan_to_value for r in rows}) == 1


def test_dscr_none_when_no_debt_service() -> None:
    """Edge case: 100% equity — no loan, DSCR undefined."""
    listing = Listing(800_000.0, 0.07)
    loan = LoanTerms(1.0, 0.06, 30, 10)  # 100% down → no loan
    sweep = CapRateSweep(0.07, 0.01, 0, 0)
    rows = build_cap_rate_scenarios(listing, loan, sweep)
    assert rows[0].debt_service_coverage_ratio is None
    assert math.isclose(
        rows[0].cash_on_cash,
        rows[0].net_operating_income / listing.purchase_price,
        rel_tol=1e-9,
    )


def test_cap_rate_rows_carry_listing_purchase_price() -> None:
    listing = Listing(purchase_price=1_234_000.0, listing_cap_rate=0.07)
    loan = LoanTerms(0.22, 0.06, 30, 10)
    rows = build_cap_rate_scenarios(listing, loan, CapRateSweep(0.07, 0.01, 0, 0))
    assert all(r.purchase_price == listing.purchase_price for r in rows)
