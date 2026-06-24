"""Combine listing, loan, and sweeps into comparable scenario rows."""

from __future__ import annotations

import math
from dataclasses import dataclass

from cre_calcs.income import StatedNoi
from cre_calcs.metrics import (
    cash_on_cash,
    debt_service_coverage_ratio,
    equity_invested,
    loan_amount,
    loan_to_value,
)
from cre_calcs.model import CapRateSweep, DownPaymentSweep, Listing, LoanRateTerms, LoanTerms
from cre_calcs.mortgage import annual_debt_service, remaining_balance_after_months


@dataclass(frozen=True, slots=True)
class ScenarioRow:
    """One underwriting line (cap band, implied price, or financing slice)."""

    display_label: str
    net_operating_income: float
    annual_debt_service: float
    cash_on_cash: float
    debt_service_coverage_ratio: float | None
    loan_to_value: float
    purchase_price: float
    assumed_cap_rate: float | None = None
    implied_purchase_price: float | None = None
    effective_down_payment_fraction: float | None = None
    loan_balance: float | None = None
    current_value: float | None = None


@dataclass(frozen=True, slots=True)
class YearProjectionRow:
    """One year of operating and financing metrics at a fixed acquisition."""

    year: int
    net_operating_income: float
    annual_debt_service: float
    cash_flow: float
    cash_on_cash: float
    loan_balance: float
    property_value: float
    debt_service_coverage_ratio: float | None
    loan_to_value: float
    equity: float


def _row_metrics(
    *,
    display_label: str,
    purchase_price: float,
    net_operating_income: float,
    loan: LoanTerms,
    assumed_cap_rate: float | None = None,
    implied_purchase_price: float | None = None,
    effective_down_payment_fraction: float | None = None,
    loan_to_value_override: float | None = None,
    loan_balance: float | None = None,
    current_value: float | None = None,
) -> ScenarioRow:
    listing = Listing(
        purchase_price=purchase_price,
        listing_cap_rate=0.06 if assumed_cap_rate is None else assumed_cap_rate,
        percentage_rent_annual=0.0,
    )
    principal = loan_amount(listing, loan)
    ads = annual_debt_service(
        principal=principal,
        annual_interest_rate=loan.annual_interest_rate,
        amortization_years=loan.amortization_years,
    )
    equity = equity_invested(listing, loan)
    ltv = loan_to_value_override if loan_to_value_override is not None else loan_to_value(listing, loan)
    coc = cash_on_cash(net_operating_income, ads, equity) if equity > 0 else float("nan")
    dscr = debt_service_coverage_ratio(net_operating_income, ads)
    return ScenarioRow(
        display_label=display_label,
        net_operating_income=net_operating_income,
        annual_debt_service=ads,
        cash_on_cash=coc,
        debt_service_coverage_ratio=dscr,
        loan_to_value=ltv,
        purchase_price=purchase_price,
        assumed_cap_rate=assumed_cap_rate,
        implied_purchase_price=implied_purchase_price,
        effective_down_payment_fraction=effective_down_payment_fraction,
        loan_balance=loan_balance,
        current_value=current_value,
    )


def _amortized_ltv(
    *,
    principal: float,
    loan: LoanTerms,
    months_elapsed: int,
    property_value: float,
) -> tuple[float, float]:
    """Return (loan balance, LTV) at start of analysis year from acquisition."""
    balance = remaining_balance_after_months(
        principal=principal,
        annual_interest_rate=loan.annual_interest_rate,
        amortization_years=loan.amortization_years,
        months_elapsed=months_elapsed,
    )
    if property_value <= 0.0:
        raise ValueError("property_value must be positive for LTV")
    return balance, balance / property_value


def build_cap_rate_scenarios(
    listing: Listing,
    loan: LoanTerms,
    sweep: CapRateSweep,
) -> list[ScenarioRow]:
    """Fixed purchase price: NOI moves with assumed cap (price × cap)."""
    rows: list[ScenarioRow] = []
    for cap in sweep.cap_rates_low_to_high():
        noi = listing.net_operating_income_at_cap(cap)
        rows.append(
            _row_metrics(
                display_label=f"{cap:.2%}",
                purchase_price=listing.purchase_price,
                net_operating_income=noi,
                loan=loan,
                assumed_cap_rate=cap,
                implied_purchase_price=None,
                effective_down_payment_fraction=None,
            )
        )
    return rows


def build_cap_implied_price_scenarios(
    *,
    operating_income: float,
    down_payment_fraction: float,
    loan_rates: LoanRateTerms,
    cap_sweep: CapRateSweep,
    going_in_income: float | None = None,
    months_elapsed: int = 0,
) -> list[ScenarioRow]:
    """Going-in cap bands: implied purchase price = going-in NOI ÷ cap.

    When ``going_in_income`` differs from ``operating_income``, price and loan
  sizing stay anchored at acquisition while row NOI / DSCR / LTV reflect the
    analysis year (amortized balance over appreciated value).
    """
    anchor_noi = operating_income if going_in_income is None else going_in_income
    if months_elapsed < 0:
        raise ValueError("months_elapsed cannot be negative")
    rows: list[ScenarioRow] = []
    for cap in cap_sweep.cap_rates_low_to_high():
        price = anchor_noi / cap
        loan = loan_rates.with_down_payment(down_payment_fraction)
        principal = price * (1.0 - down_payment_fraction)
        property_value = operating_income / cap
        if months_elapsed > 0:
            balance, ltv = _amortized_ltv(
                principal=principal,
                loan=loan,
                months_elapsed=months_elapsed,
                property_value=property_value,
            )
        else:
            balance = principal
            ltv = None
        rows.append(
            _row_metrics(
                display_label=f"{cap:.2%}",
                purchase_price=price,
                net_operating_income=operating_income,
                loan=loan,
                assumed_cap_rate=cap,
                implied_purchase_price=price,
                effective_down_payment_fraction=down_payment_fraction,
                loan_to_value_override=ltv,
                loan_balance=balance if months_elapsed > 0 else None,
                current_value=property_value if months_elapsed > 0 else None,
            )
        )
    return rows


def build_year_projection(
    *,
    going_in_price: float,
    stated_noi: StatedNoi,
    loan: LoanTerms,
    valuation_cap_rate: float,
    years: int,
) -> list[YearProjectionRow]:
    """Year-by-year NOI, cash flow, DSCR, and LTV at a fixed acquisition price."""
    if going_in_price <= 0.0:
        raise ValueError("going_in_price must be positive")
    if valuation_cap_rate <= 0.0:
        raise ValueError("valuation_cap_rate must be positive")
    if years < 1:
        raise ValueError("years must be at least 1")

    principal = going_in_price * (1.0 - loan.down_payment_fraction)
    equity = going_in_price * loan.down_payment_fraction
    ads = annual_debt_service(
        principal=principal,
        annual_interest_rate=loan.annual_interest_rate,
        amortization_years=loan.amortization_years,
    )
    rows: list[YearProjectionRow] = []
    for year in range(1, years + 1):
        noi = stated_noi.operating_income_year(year)
        property_value = noi / valuation_cap_rate
        months_elapsed = (year - 1) * 12
        balance, ltv = _amortized_ltv(
            principal=principal,
            loan=loan,
            months_elapsed=months_elapsed,
            property_value=property_value,
        )
        cash_flow = noi - ads
        coc = cash_on_cash(noi, ads, equity) if equity > 0 else float("nan")
        dscr = debt_service_coverage_ratio(noi, ads)
        rows.append(
            YearProjectionRow(
                year=year,
                net_operating_income=noi,
                annual_debt_service=ads,
                cash_flow=cash_flow,
                cash_on_cash=coc,
                loan_balance=balance,
                property_value=property_value,
                debt_service_coverage_ratio=dscr,
                loan_to_value=ltv,
                equity=equity,
            )
        )
    return rows


def inject_offer_cap_row(
    rows: list[ScenarioRow],
    *,
    operating_income: float,
    offer_price: float,
    list_price: float,
    loan: LoanTerms,
    implied_price_mode: bool,
    down_payment_fraction: float | None = None,
    going_in_income: float | None = None,
    months_elapsed: int = 0,
    threshold_fraction: float = 0.01,
) -> list[ScenarioRow]:
    """Insert a cap row for the purchase-price offer when it diverges from list (NOI ÷ cap)."""
    if list_price <= 0 or offer_price <= 0:
        return rows
    if abs(offer_price - list_price) / list_price <= threshold_fraction:
        return rows

    anchor_noi = operating_income if going_in_income is None else going_in_income
    offer_cap = anchor_noi / offer_price
    if offer_cap <= 0:
        return rows

    for r in rows:
        if r.assumed_cap_rate is not None and math.isclose(
            r.assumed_cap_rate, offer_cap, rel_tol=1e-9, abs_tol=1e-12
        ):
            return rows

    if implied_price_mode:
        principal = offer_price * (1.0 - (down_payment_fraction or loan.down_payment_fraction))
        property_value = operating_income / offer_cap if offer_cap > 0 else 0.0
        if months_elapsed > 0 and property_value > 0:
            balance, ltv = _amortized_ltv(
                principal=principal,
                loan=loan,
                months_elapsed=months_elapsed,
                property_value=property_value,
            )
        else:
            balance = principal
            ltv = None
        row = _row_metrics(
            display_label=f"{offer_cap:.2%}",
            purchase_price=offer_price,
            net_operating_income=operating_income,
            loan=loan,
            assumed_cap_rate=offer_cap,
            implied_purchase_price=offer_price,
            effective_down_payment_fraction=down_payment_fraction,
            loan_to_value_override=ltv,
            loan_balance=balance if months_elapsed > 0 else None,
            current_value=property_value if months_elapsed > 0 else None,
        )
    else:
        row = _row_metrics(
            display_label=f"{offer_cap:.2%}",
            purchase_price=offer_price,
            net_operating_income=operating_income,
            loan=loan,
            assumed_cap_rate=offer_cap,
            implied_purchase_price=None,
            effective_down_payment_fraction=None,
        )

    insert_at = len(rows)
    for i, r in enumerate(rows):
        if r.assumed_cap_rate is not None and r.assumed_cap_rate > offer_cap:
            insert_at = i
            break

    out = list(rows)
    out.insert(insert_at, row)
    return out


def build_down_payment_scenarios(
    *,
    purchase_price: float,
    operating_income: float,
    listing_cap_for_display: float,
    loan_rates: LoanRateTerms,
    sweep: DownPaymentSweep,
) -> list[ScenarioRow]:
    """Equity / loan sizing bands at a fixed price and NOI."""
    rows: list[ScenarioRow] = []
    for down in sweep.down_payment_fractions_low_to_high():
        loan = loan_rates.with_down_payment(down)
        rows.append(
            _row_metrics(
                display_label=f"{down:.1%} down",
                purchase_price=purchase_price,
                net_operating_income=operating_income,
                loan=loan,
                assumed_cap_rate=listing_cap_for_display,
                implied_purchase_price=None,
                effective_down_payment_fraction=down,
            )
        )
    return rows
