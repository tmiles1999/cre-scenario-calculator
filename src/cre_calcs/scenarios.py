"""Combine listing, loan, and sweeps into comparable scenario rows."""

from __future__ import annotations

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
