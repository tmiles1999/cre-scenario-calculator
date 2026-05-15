"""Render scenario grids for console or reports."""

from __future__ import annotations

import math

from tabulate import tabulate

from cre_calcs.model import Listing, LoanTerms
from cre_calcs.mortgage import remaining_balance_after_months
from cre_calcs.scenarios import ScenarioRow


def balloon_snapshot_line(purchase_price: float, loan: LoanTerms) -> str:
    """One-line balloon balance estimate for a given price and loan."""
    principal = purchase_price * (1.0 - loan.down_payment_fraction)
    balloon_balance = remaining_balance_after_months(
        principal=principal,
        annual_interest_rate=loan.annual_interest_rate,
        amortization_years=loan.amortization_years,
        months_elapsed=loan.balloon_years * 12,
    )
    return (
        f"Balloon snapshot at ${purchase_price:,.0f} price, "
        f"{loan.down_payment_fraction:.0%} down: estimated balance ${balloon_balance:,.0f}"
    )


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


def format_scenario_rows(
    rows: list[ScenarioRow],
    *,
    summary_lines: list[str],
    balloon_purchase_price: float | None = None,
    balloon_loan: LoanTerms | None = None,
) -> str:
    """Format rows with optional balloon snapshot (same amort assumptions as ``balloon_loan``)."""
    extra: list[str] = []
    if balloon_purchase_price is not None and balloon_loan is not None:
        extra.append(balloon_snapshot_line(balloon_purchase_price, balloon_loan))

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
    return format_scenario_rows(
        rows,
        summary_lines=summary,
        balloon_purchase_price=listing.purchase_price,
        balloon_loan=loan,
    )
