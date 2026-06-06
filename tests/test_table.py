"""Smoke test for table rendering."""

import math

from cre_calcs.model import CapRateSweep, Listing, LoanRateTerms, LoanTerms
from cre_calcs.scenarios import build_cap_implied_price_scenarios, build_cap_rate_scenarios
from cre_calcs.mortgage import annual_debt_service
from cre_calcs.table import (
    balloon_context_lines,
    format_scenario_table,
    scenario_rows_matrix,
)


def test_balloon_context_lines_list_offer_and_cash_flow() -> None:
    list_price = 2_596_800.0
    offer_price = 2_300_000.0
    noi = 155_808.0
    loan = LoanTerms(0.25, 0.065, 25, 5)
    lines = balloon_context_lines(
        loan,
        net_operating_income=noi,
        list_price=list_price,
        offer_price=offer_price,
    )
    assert len(lines) == 3
    assert lines[0] == (
        "Balloon snapshot at list $2,596,800 price, 25% down ($649,200): "
        "estimated balance $1,763,789"
    )
    assert lines[1] == (
        "Balloon snapshot at offer $2,300,000 price, 25% down ($575,000): "
        "estimated balance $1,562,197"
    )
    principal = offer_price * (1.0 - loan.down_payment_fraction)
    ads = annual_debt_service(principal, loan.annual_interest_rate, loan.amortization_years)
    annual_cf = noi - ads
    assert lines[2] == (
        f"Year-one cash flow at offer $2,300,000 price, "
        f"estimated ${annual_cf / 12.0:,.0f}/mo (${annual_cf:,.0f}/yr)"
    )
    assert "Balloon payment" not in "\n".join(lines)


def test_format_scenario_table_includes_headers_and_balloon_context() -> None:
    listing = Listing(1_500_000.0, 0.065)
    loan = LoanTerms(0.28, 0.0675, 25, 10)
    sweep = CapRateSweep(0.065, 0.005, 1, 1)
    rows = build_cap_rate_scenarios(listing, loan, sweep)
    text = format_scenario_table(listing, loan, rows)
    assert "Purchase" in text
    assert "Year-one cash flow" in text
    assert "Balloon payment" not in text
    assert "LTV" in text
    assert "DSCR" in text


def test_scenario_rows_matrix_headers_and_data() -> None:
    listing = Listing(1_000_000.0, 0.07)
    loan = LoanTerms(0.25, 0.06, 30, 10)
    sweep = CapRateSweep(0.07, 0.01, 0, 1)
    rows = build_cap_rate_scenarios(listing, loan, sweep)
    headers, data = scenario_rows_matrix(rows)
    assert headers[0] == "Scenario (Cap Rate)"
    assert "NOI" in headers
    assert "LTV" in headers
    assert len(data) == len(rows)
    assert all(len(r) == len(headers) for r in data)


def test_scenario_rows_matrix_includes_down_for_implied_price() -> None:
    noi = 600_000.0
    down = 0.25
    rows = build_cap_implied_price_scenarios(
        operating_income=noi,
        down_payment_fraction=down,
        loan_rates=LoanRateTerms(0.06, 30, 10),
        cap_sweep=CapRateSweep(0.06, 0.01, 1, 1),
    )
    headers, data = scenario_rows_matrix(rows)
    assert headers[0] == "Scenario (Cap Rate)"
    assert "Implied Price" in headers
    assert "Down ($)" in headers
    assert "NOI" not in headers
    assert headers.index("Down ($)") == headers.index("Implied Price") + 1
    assert headers[headers.index("Down ($)") + 1] == "Debt Service (Yr)"
    down_col = headers.index("Down ($)")
    for row, r in zip(data, rows, strict=True):
        expected_equity = r.purchase_price * down
        assert row[down_col] == f"${expected_equity:,.0f}"
