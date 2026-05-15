"""Mortgage math: level P&I from amortization schedule."""

from __future__ import annotations


def annual_debt_service(
    principal: float,
    annual_interest_rate: float,
    amortization_years: int,
) -> float:
    """Total P&I in a full year (12 identical monthly payments)."""
    if principal < 0:
        raise ValueError("principal cannot be negative")
    if principal == 0.0:
        return 0.0
    if annual_interest_rate <= 0:
        raise ValueError("annual_interest_rate must be positive")
    if amortization_years <= 0:
        raise ValueError("amortization_years must be positive")

    monthly_rate = annual_interest_rate / 12.0
    n_months = amortization_years * 12
    factor = (1.0 + monthly_rate) ** n_months
    monthly_payment = principal * (monthly_rate * factor) / (factor - 1.0)
    return 12.0 * monthly_payment


def remaining_balance_after_months(
    principal: float,
    annual_interest_rate: float,
    amortization_years: int,
    months_elapsed: int,
) -> float:
    """Outstanding principal after months_elapsed on a level-payment schedule."""
    if principal <= 0.0:
        return 0.0
    if months_elapsed <= 0:
        return principal
    monthly_rate = annual_interest_rate / 12.0
    n_months = amortization_years * 12
    if months_elapsed >= n_months:
        return 0.0

    monthly_payment = annual_debt_service(
        principal, annual_interest_rate, amortization_years
    ) / 12.0
    balance = principal
    for _ in range(months_elapsed):
        interest = balance * monthly_rate
        principal_paid = monthly_payment - interest
        balance -= principal_paid
    return max(balance, 0.0)
