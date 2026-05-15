"""Tests for LTV, cash-on-cash, and DSCR."""

import math

from cre_calcs.metrics import cash_on_cash, debt_service_coverage_ratio, loan_to_value
from cre_calcs.model import Listing, LoanTerms
from cre_calcs.mortgage import annual_debt_service


def test_loan_to_value() -> None:
    listing = Listing(purchase_price=2_000_000.0, listing_cap_rate=0.06)
    loan = LoanTerms(
        down_payment_fraction=0.25,
        annual_interest_rate=0.065,
        amortization_years=25,
        balloon_years=10,
    )
    assert math.isclose(loan_to_value(listing, loan), 0.75, rel_tol=1e-12)


def test_cash_on_cash_and_dscr() -> None:
    """NOI = price * cap; equity = down * price; CF = NOI - ADS."""
    listing = Listing(purchase_price=1_000_000.0, listing_cap_rate=0.07)
    loan = LoanTerms(
        down_payment_fraction=0.20,
        annual_interest_rate=0.06,
        amortization_years=30,
        balloon_years=10,
    )
    noi = listing.net_operating_income_at_cap(0.07)
    loan_amount = listing.purchase_price * (1.0 - loan.down_payment_fraction)
    ads = annual_debt_service(
        principal=loan_amount,
        annual_interest_rate=loan.annual_interest_rate,
        amortization_years=loan.amortization_years,
    )
    equity = listing.purchase_price * loan.down_payment_fraction
    assert math.isclose(cash_on_cash(noi, ads, equity), (noi - ads) / equity, rel_tol=1e-9)
    assert math.isclose(
        debt_service_coverage_ratio(noi, ads),
        noi / ads,
        rel_tol=1e-9,
    )


def test_dscr_zero_debt_service() -> None:
    assert debt_service_coverage_ratio(100_000.0, 0.0) is None
