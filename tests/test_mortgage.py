"""Tests for amortizing debt service with optional balloon maturity."""

import math

import pytest

from cre_calcs.mortgage import annual_debt_service, remaining_balance_after_months


def test_annual_debt_service_matches_known_amortization() -> None:
    """Classic P&I: payment derived from amort period, not balloon."""
    principal = 800_000.0
    annual_rate = 0.06
    amortization_years = 30
    monthly_rate = annual_rate / 12.0
    n_months = amortization_years * 12
    monthly = principal * (monthly_rate * (1 + monthly_rate) ** n_months) / (
        (1 + monthly_rate) ** n_months - 1
    )
    expected_annual = 12 * monthly

    assert math.isclose(
        annual_debt_service(
            principal=principal,
            annual_interest_rate=annual_rate,
            amortization_years=amortization_years,
        ),
        expected_annual,
        rel_tol=1e-9,
    )


def test_remaining_balance_after_balloon_horizon() -> None:
    """After 10 years of paydown on a 30-year schedule, balance is below principal."""
    principal = 1_000_000.0
    annual_rate = 0.055
    amortization_years = 30
    balloon_years = 10
    bal = remaining_balance_after_months(
        principal=principal,
        annual_interest_rate=annual_rate,
        amortization_years=amortization_years,
        months_elapsed=balloon_years * 12,
    )
    assert bal < principal
    assert bal > 0


def test_zero_rate_raises() -> None:
    with pytest.raises(ValueError, match="annual_interest_rate"):
        annual_debt_service(100_000, 0.0, 30)


def test_non_positive_amortization_raises() -> None:
    with pytest.raises(ValueError, match="amortization"):
        annual_debt_service(100_000, 0.05, 0)
