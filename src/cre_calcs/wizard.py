"""Interactive guided underwriting (questionary)."""

from __future__ import annotations

import sys

import questionary

from cre_calcs.income import StatedNoi
from cre_calcs.model import CapRateSweep, DownPaymentSweep, Listing, LoanRateTerms
from cre_calcs.money_parse import parse_money_amount
from cre_calcs.percent_parse import parse_display_percent_to_decimal
from cre_calcs.scenarios import (
    build_cap_implied_price_scenarios,
    build_cap_rate_scenarios,
    build_down_payment_scenarios,
)
from cre_calcs.table import format_scenario_rows, format_scenario_table


def _positive_percent(text: str) -> float:
    r = parse_display_percent_to_decimal(text)
    if r <= 0:
        raise ValueError("percentage must be greater than zero")
    return r


def _non_negative_percent(text: str) -> float:
    r = parse_display_percent_to_decimal(text)
    if r < 0:
        raise ValueError("percentage cannot be negative")
    return r


def _parse_fraction(text: str) -> float:
    x = float(text.strip().replace("%", ""))
    if x > 1.0:
        x /= 100.0
    if not 0.0 <= x <= 1.0:
        raise ValueError("must be between 0 and 100%")
    return x


def _money(text: str) -> float:
    return parse_money_amount(text)


def _int(text: str) -> int:
    v = int(text.strip())
    return v


def _optional_escalator() -> float:
    if not questionary.confirm("Apply annual escalator to income?", default=False).ask():
        return 0.0
    raw = questionary.text(
        "Annual escalator (% per year on the chosen base, e.g. 3 for 3%):",
        default="3",
    ).ask()
    if raw is None:
        return 0.0
    return _non_negative_percent(raw)


def _income_stated_interactive() -> StatedNoi:
    y1 = _money(
        questionary.text("Year-1 NOI or total contract rent (e.g. 155.808k):", default="155.808k").ask()
        or "0"
    )
    esc = _optional_escalator()
    return StatedNoi(year1_noi=y1, annual_escalator_fraction=esc)


def _loan_rates_interactive() -> LoanRateTerms:
    rate = _positive_percent(
        questionary.text(
            "Loan rate (%, e.g. 6.5 for 6.5%):",
            default="6.5",
        ).ask()
        or "6.5"
    )
    amort = _int(questionary.text("Amortization (years):", default="25").ask() or "25")
    balloon = _int(questionary.text("Balloon / maturity (years):", default="5").ask() or "5")
    return LoanRateTerms(
        annual_interest_rate=rate,
        amortization_years=amort,
        balloon_years=balloon,
    )


def _cap_sweep_interactive() -> CapRateSweep:
    center = _positive_percent(
        questionary.text(
            "Center going-in cap (%, e.g. 6 for 6%):",
            default="6",
        ).ask()
        or "6"
    )
    step = _positive_percent(
        questionary.text(
            "Cap sweep step (% per band, e.g. 0.1 for 0.1% = 10 bps between rows):",
            default="0.1",
        ).ask()
        or "0.1"
    )
    below = _int(questionary.text("Steps below center:", default="0").ask() or "0")
    above = _int(questionary.text("Steps above center:", default="15").ask() or "15")
    return CapRateSweep(
        center_cap_rate=center,
        step=step,
        steps_below=below,
        steps_above=above,
    )


def _down_sweep_interactive() -> DownPaymentSweep:
    center = _parse_fraction(
        questionary.text("Center down payment (e.g. 35 or 0.35):", default="35").ask() or "35"
    )
    step = _parse_fraction(
        questionary.text("Sweep step (e.g. 5 for five percentage points):", default="5").ask() or "5"
    )
    below = _int(questionary.text("Steps below center:", default="2").ask() or "2")
    above = _int(questionary.text("Steps above center:", default="2").ask() or "2")
    return DownPaymentSweep(
        center_down_payment_fraction=center,
        step=step,
        steps_below=below,
        steps_above=above,
    )


def run_wizard() -> None:
    print("\n=== CRE scenarios (interactive) ===\n", flush=True)

    sweep = questionary.select(
        "What should we sweep?",
        choices=[
            questionary.Choice(
                "Cap rates at a fixed purchase price (NOI = price × cap)",
                value="cap_fixed",
            ),
            questionary.Choice(
                "Cap rates → implied offer price (stated NOI ÷ cap)",
                value="cap_price",
            ),
            questionary.Choice(
                "Down payment → LTV & cash-on-cash (fixed price & NOI)",
                value="down",
            ),
        ],
    ).ask()
    if sweep is None:
        sys.exit(0)

    if sweep == "cap_fixed":
        price = _money(
            questionary.text("Purchase / offer price (e.g. 2.597M):", default="2.597M").ask() or "0"
        )
        listing_cap = _positive_percent(
            questionary.text("Listing / center cap (%, e.g. 6.25 for 6.25%):", default="6.25").ask()
            or "6.25"
        )
        down = _parse_fraction(
            questionary.text("Down payment (e.g. 25 or 0.25):", default="25").ask() or "25"
        )
        rates = _loan_rates_interactive()
        loan = rates.with_down_payment(down)
        listing = Listing(
            purchase_price=price,
            listing_cap_rate=listing_cap,
        )
        cap_sweep = _cap_sweep_interactive()
        rows = build_cap_rate_scenarios(listing, loan, cap_sweep)
        print(format_scenario_table(listing, loan, rows))
        return

    analysis_year = _int(
        questionary.text(
            "Analysis year for NOI (1 = first year, use 2+ if escalators apply):",
            default="1",
        ).ask()
        or "1"
    )
    income = _income_stated_interactive()
    noi = income.operating_income_year(analysis_year)

    rates = _loan_rates_interactive()

    if sweep == "cap_price":
        down = _parse_fraction(
            questionary.text("Down payment for implied price scenarios (e.g. 25):", default="25").ask()
            or "25"
        )
        cap_sweep = _cap_sweep_interactive()
        rows = build_cap_implied_price_scenarios(
            operating_income=noi,
            down_payment_fraction=down,
            loan_rates=rates,
            cap_sweep=cap_sweep,
        )
        loan = rates.with_down_payment(down)
        center_cap = cap_sweep.center_cap_rate
        ref_price = noi / center_cap
        summary = [
            f"Sweep: cap → implied price  |  NOI (Y{analysis_year}) ${noi:,.0f}  |  "
            f"Down {down:.0%}  |  Loan {rates.annual_interest_rate:.2%} "
            f"{rates.amortization_years}yr / {rates.balloon_years}yr balloon  |  "
            f"Ref. price @ {center_cap:.2%} cap ≈ ${ref_price:,.0f}",
        ]
        print(
            format_scenario_rows(
                rows,
                summary_lines=summary,
                balloon_loan=loan,
                balloon_net_operating_income=noi,
                balloon_list_price=ref_price,
            )
        )
        return

    # down payment sweep
    price = _money(
        questionary.text("Fixed purchase price (e.g. 2.597M):", default="2.597M").ask() or "0"
    )
    listing_cap = _positive_percent(
        questionary.text(
            "Reference listing cap for labels (%, e.g. 6.25 for 6.25%):",
            default="6.25",
        ).ask()
        or "6.25"
    )
    down_sweep = _down_sweep_interactive()
    rows = build_down_payment_scenarios(
        purchase_price=price,
        operating_income=noi,
        listing_cap_for_display=listing_cap,
        loan_rates=rates,
        sweep=down_sweep,
    )
    center_down = down_sweep.center_down_payment_fraction
    loan = rates.with_down_payment(center_down)
    summary = [
        f"Sweep: down payment  |  Price ${price:,.0f}  |  NOI (Y{analysis_year}) ${noi:,.0f}  |  "
        f"Ref. cap {listing_cap:.2%}  |  Loan {rates.annual_interest_rate:.2%} "
        f"{rates.amortization_years}yr / {rates.balloon_years}yr balloon",
    ]
    print(
        format_scenario_rows(
            rows,
            summary_lines=summary,
            balloon_loan=loan,
            balloon_net_operating_income=noi,
            balloon_list_price=noi / listing_cap,
            balloon_offer_price=price,
        )
    )
