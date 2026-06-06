"""Combine listing, loan, and sweeps into comparable scenario rows."""

from __future__ import annotations

import math
from dataclasses import dataclass

from cre_calcs.metrics import (
    cash_on_cash,
    debt_service_coverage_ratio,
    equity_invested,
    loan_amount,
    loan_to_value,
)
from cre_calcs.model import CapRateSweep, DownPaymentSweep, Listing, LoanRateTerms, LoanTerms
from cre_calcs.mortgage import annual_debt_service


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


def _row_metrics(
    *,
    display_label: str,
    purchase_price: float,
    net_operating_income: float,
    loan: LoanTerms,
    assumed_cap_rate: float | None = None,
    implied_purchase_price: float | None = None,
    effective_down_payment_fraction: float | None = None,
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
    ltv = loan_to_value(listing, loan)
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
    )


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
) -> list[ScenarioRow]:
    """Going-in cap bands: implied purchase price = NOI ÷ cap (same NOI each row)."""
    rows: list[ScenarioRow] = []
    for cap in cap_sweep.cap_rates_low_to_high():
        price = operating_income / cap
        loan = loan_rates.with_down_payment(down_payment_fraction)
        rows.append(
            _row_metrics(
                display_label=f"{cap:.2%}",
                purchase_price=price,
                net_operating_income=operating_income,
                loan=loan,
                assumed_cap_rate=cap,
                implied_purchase_price=price,
                effective_down_payment_fraction=down_payment_fraction,
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
    threshold_fraction: float = 0.01,
) -> list[ScenarioRow]:
    """Insert a cap row for the purchase-price offer when it diverges from list (NOI ÷ cap)."""
    if list_price <= 0 or offer_price <= 0:
        return rows
    if abs(offer_price - list_price) / list_price <= threshold_fraction:
        return rows

    offer_cap = operating_income / offer_price
    if offer_cap <= 0:
        return rows

    for r in rows:
        if r.assumed_cap_rate is not None and math.isclose(
            r.assumed_cap_rate, offer_cap, rel_tol=1e-9, abs_tol=1e-12
        ):
            return rows

    if implied_price_mode:
        row = _row_metrics(
            display_label=f"{offer_cap:.2%}",
            purchase_price=offer_price,
            net_operating_income=operating_income,
            loan=loan,
            assumed_cap_rate=offer_cap,
            implied_purchase_price=offer_price,
            effective_down_payment_fraction=down_payment_fraction,
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
