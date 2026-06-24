"""Render scenario grids for console or reports."""

from __future__ import annotations

import math

from tabulate import tabulate

from cre_calcs.model import Listing, LoanTerms
from cre_calcs.mortgage import annual_debt_service, remaining_balance_after_months
from cre_calcs.scenarios import ScenarioRow, YearProjectionRow


def _balloon_balance(purchase_price: float, loan: LoanTerms) -> float:
    principal = purchase_price * (1.0 - loan.down_payment_fraction)
    return remaining_balance_after_months(
        principal=principal,
        annual_interest_rate=loan.annual_interest_rate,
        amortization_years=loan.amortization_years,
        months_elapsed=loan.balloon_years * 12,
    )


def _price_phrase(purchase_price: float, *, price_label: str | None) -> str:
    if price_label:
        return f"at {price_label} ${purchase_price:,.0f}"
    return f"at ${purchase_price:,.0f}"


def offering_price(net_operating_income: float, cap_rate: float) -> float:
    """List/offering price implied by stated NOI and going-in cap (NOI ÷ cap)."""
    if cap_rate <= 0:
        raise ValueError("cap_rate must be positive")
    return net_operating_income / cap_rate


def balloon_snapshot_line(
    purchase_price: float,
    loan: LoanTerms,
    *,
    price_label: str | None = None,
) -> str:
    """One-line balloon balance estimate for a given price and loan."""
    balloon_balance = _balloon_balance(purchase_price, loan)
    equity = purchase_price * loan.down_payment_fraction
    return (
        f"Balloon snapshot {_price_phrase(purchase_price, price_label=price_label)} price, "
        f"{loan.down_payment_fraction:.0%} down (${equity:,.0f}): "
        f"estimated balance ${balloon_balance:,.0f}"
    )


def balloon_cash_flow_line(
    purchase_price: float,
    loan: LoanTerms,
    *,
    net_operating_income: float,
    price_label: str = "offer",
    income_year: int | None = None,
) -> str:
    """Pre-tax cash flow (NOI − debt service) at a fixed price."""
    principal = purchase_price * (1.0 - loan.down_payment_fraction)
    ads = annual_debt_service(
        principal=principal,
        annual_interest_rate=loan.annual_interest_rate,
        amortization_years=loan.amortization_years,
    )
    annual_cf = net_operating_income - ads
    monthly_cf = annual_cf / 12.0
    year_phrase = "Year-one" if income_year in (None, 1) else f"Year {income_year}"
    return (
        f"{year_phrase} cash flow {_price_phrase(purchase_price, price_label=price_label)} price, "
        f"estimated ${monthly_cf:,.0f}/mo (${annual_cf:,.0f}/yr)"
    )


def balloon_exit_line(
    loan: LoanTerms,
    *,
    purchase_price: float,
    exit_noi: float,
    valuation_cap_rate: float,
    price_label: str = "offer",
) -> str:
    """Exit valuation at balloon using escalated NOI and amortized loan balance."""
    if valuation_cap_rate <= 0:
        raise ValueError("valuation_cap_rate must be positive")
    exit_value = exit_noi / valuation_cap_rate
    balloon_balance = _balloon_balance(purchase_price, loan)
    net_proceeds = exit_value - balloon_balance
    return (
        f"Balloon exit (year {loan.balloon_years}) at {price_label} price: "
        f"value ${exit_value:,.0f} (NOI ${exit_noi:,.0f} ÷ {valuation_cap_rate:.2%}), "
        f"balance ${balloon_balance:,.0f}, net proceeds ${net_proceeds:,.0f}"
    )


def balloon_context_lines(
    loan: LoanTerms,
    *,
    net_operating_income: float | None = None,
    list_price: float | None = None,
    offer_price: float | None = None,
    exit_noi: float | None = None,
    valuation_cap_rate: float | None = None,
    income_year: int | None = None,
) -> list[str]:
    """List (NOI ÷ cap) and offer (purchase price) balloon snapshots plus offer cash flow."""
    lines: list[str] = []
    if list_price is not None:
        lines.append(balloon_snapshot_line(list_price, loan, price_label="list"))
    if offer_price is not None:
        if list_price is None or not math.isclose(
            list_price, offer_price, rel_tol=1e-9, abs_tol=0.5
        ):
            lines.append(balloon_snapshot_line(offer_price, loan, price_label="offer"))
        if net_operating_income is not None:
            lines.append(
                balloon_cash_flow_line(
                    offer_price,
                    loan,
                    net_operating_income=net_operating_income,
                    price_label="offer",
                    income_year=income_year,
                )
            )
        if exit_noi is not None and valuation_cap_rate is not None:
            lines.append(
                balloon_exit_line(
                    loan,
                    purchase_price=offer_price,
                    exit_noi=exit_noi,
                    valuation_cap_rate=valuation_cap_rate,
                    price_label="offer",
                )
            )
    return lines


def scenario_rows_matrix(rows: list[ScenarioRow]) -> tuple[list[str], list[list[str]]]:
    """Headers and formatted cell rows for Markdown, Streamlit, or PDF tables."""
    show_implied = any(r.implied_purchase_price is not None for r in rows)
    show_down = any(r.effective_down_payment_fraction is not None for r in rows)
    # Down sweep: equity fraction varies per row, no implied price. Cap grids: cap varies (fixed or implied price).
    scenario_header = (
        "Scenario (Down)" if show_down and not show_implied else "Scenario (Cap Rate)"
    )
    # Implied-price runs use the same NOI for every row; show it in summary only, not per row.
    show_noi_column = not show_implied
    headers = [scenario_header]
    if show_implied:
        headers.append("Implied Price")
    if show_down:
        headers.append("Down ($)")
    if show_noi_column:
        headers.append("NOI")
    headers.extend(["Debt Service (Yr)", "Cash-on-Cash", "DSCR", "LTV"])

    data: list[list[str]] = []
    for r in rows:
        dscr = "" if r.debt_service_coverage_ratio is None else f"{r.debt_service_coverage_ratio:.2f}x"
        coc = "n/a" if math.isnan(r.cash_on_cash) else f"{r.cash_on_cash:.2%}"
        row_out: list[str] = [r.display_label]
        if show_implied:
            ip = r.implied_purchase_price
            row_out.append("" if ip is None else f"${ip:,.0f}")
        if show_down:
            d = r.effective_down_payment_fraction
            if d is None:
                row_out.append("")
            else:
                equity_dollars = r.purchase_price * d
                row_out.append(f"${equity_dollars:,.0f}")
        if show_noi_column:
            row_out.append(f"${r.net_operating_income:,.0f}")
        row_out.extend(
            [
                f"${r.annual_debt_service:,.0f}",
                coc,
                dscr,
                f"{r.loan_to_value:.2%}",
            ]
        )
        data.append(row_out)
    return headers, data


def year_projection_matrix(rows: list[YearProjectionRow]) -> tuple[list[str], list[list[str]]]:
    """Headers and formatted cells for a year-by-year operating projection."""
    headers = [
        "Year",
        "NOI",
        "Debt Service",
        "Cash Flow",
        "Cash-on-Cash",
        "Loan Balance",
        "Property Value",
        "DSCR",
        "LTV",
    ]
    data: list[list[str]] = []
    for r in rows:
        dscr = "" if r.debt_service_coverage_ratio is None else f"{r.debt_service_coverage_ratio:.2f}x"
        coc = "n/a" if math.isnan(r.cash_on_cash) else f"{r.cash_on_cash:.2%}"
        data.append(
            [
                str(r.year),
                f"${r.net_operating_income:,.0f}",
                f"${r.annual_debt_service:,.0f}",
                f"${r.cash_flow:,.0f}",
                coc,
                f"${r.loan_balance:,.0f}",
                f"${r.property_value:,.0f}",
                dscr,
                f"{r.loan_to_value:.2%}",
            ]
        )
    return headers, data


def format_scenario_rows(
    rows: list[ScenarioRow],
    *,
    summary_lines: list[str],
    balloon_loan: LoanTerms | None = None,
    balloon_net_operating_income: float | None = None,
    balloon_list_price: float | None = None,
    balloon_offer_price: float | None = None,
) -> str:
    """Format rows with optional balloon snapshot (same amort assumptions as ``balloon_loan``)."""
    extra: list[str] = []
    if balloon_loan is not None and (
        balloon_list_price is not None or balloon_offer_price is not None
    ):
        extra.extend(
            balloon_context_lines(
                balloon_loan,
                net_operating_income=balloon_net_operating_income,
                list_price=balloon_list_price,
                offer_price=balloon_offer_price,
            )
        )

    headers, matrix = scenario_rows_matrix(rows)
    body = tabulate(
        matrix,
        headers=headers,
        tablefmt="github",
        stralign="right",
    )
    head = "\n".join(summary_lines + extra)
    return f"{head}\n\n{body}"


def format_scenario_table(
    listing: Listing,
    loan: LoanTerms,
    rows: list[ScenarioRow],
) -> str:
    """ASCII/Markdown-friendly table for the classic fixed-price cap sweep."""
    summary = [
        f"Purchase ${listing.purchase_price:,.0f}  |  "
        f"Listing cap {listing.listing_cap_rate:.2%}  |  "
        f"Loan {loan.annual_interest_rate:.2%} {loan.amortization_years}yr amort / "
        f"{loan.balloon_years}yr balloon",
    ]
    noi = listing.net_operating_income_at_cap(listing.listing_cap_rate)
    return format_scenario_rows(
        rows,
        summary_lines=summary,
        balloon_loan=loan,
        balloon_net_operating_income=noi,
        balloon_list_price=offering_price(noi, listing.listing_cap_rate),
        balloon_offer_price=listing.purchase_price,
    )
