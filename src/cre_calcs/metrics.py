"""Return-focused underwriting ratios."""

from __future__ import annotations

from cre_calcs.model import Listing, LoanTerms


def loan_amount(listing: Listing, loan: LoanTerms) -> float:
    return listing.purchase_price * (1.0 - loan.down_payment_fraction)


def equity_invested(listing: Listing, loan: LoanTerms) -> float:
    return listing.purchase_price * loan.down_payment_fraction


def loan_to_value(listing: Listing, loan: LoanTerms) -> float:
    """Senior loan balance divided by purchase price (year-one LTV at acquisition)."""
    return loan_amount(listing, loan) / listing.purchase_price


def debt_constant(annual_debt_service: float, loan_principal: float) -> float:
    """Mortgage / debt constant: annual debt service per dollar of loan (ADS ÷ principal).

    For level-pay amortizing debt this is the first-year ratio of P&I to initial
    balance (e.g. ``0.08`` ≈ 8¢ of annual debt service per $1 of loan).
    """
    if loan_principal <= 0.0:
        if annual_debt_service == 0.0:
            return 0.0
        raise ValueError("annual_debt_service must be zero when loan_principal is not positive")
    return annual_debt_service / loan_principal


def cash_on_cash(net_operating_income: float, annual_debt_service: float, equity: float) -> float:
    """Pre-tax cash return on equity: (NOI − debt service) / equity."""
    if equity <= 0:
        raise ValueError("equity must be positive for cash-on-cash")
    return (net_operating_income - annual_debt_service) / equity


def debt_service_coverage_ratio(
    net_operating_income: float,
    annual_debt_service: float,
) -> float | None:
    """NOI / annual debt service; undefined when there is no debt service."""
    if annual_debt_service == 0.0:
        return None
    return net_operating_income / annual_debt_service
