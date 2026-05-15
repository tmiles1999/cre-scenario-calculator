#!/usr/bin/env python3
"""CLI: cap-rate sensitivity table for a stylized acquisition."""

from __future__ import annotations

import argparse

from cre_calcs.model import CapRateSweep, Listing, LoanTerms
from cre_calcs.money_parse import parse_money_amount
from cre_calcs.percent_parse import parse_display_percent_to_decimal
from cre_calcs.scenarios import build_cap_rate_scenarios
from cre_calcs.table import format_scenario_table

_DEFAULT_SWEEP_STEP = parse_display_percent_to_decimal("0.1")


def _positive_money(value: str) -> float:
    try:
        x = parse_money_amount(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from e
    if x <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return x


def _positive_percent(value: str) -> float:
    """Cap or loan rate: display percent only (e.g. 6.5 → 0.065, 0.1 → 0.001)."""
    try:
        r = parse_display_percent_to_decimal(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from e
    if r <= 0:
        raise argparse.ArgumentTypeError("percentage must be greater than zero")
    return r


def _fraction(value: str) -> float:
    """Accept 25 or 0.25 as 25% down (equity share of price, not the same as loan-rate percents)."""
    x = float(value)
    if x > 1.0:
        x /= 100.0
    if not 0.0 <= x <= 1.0:
        raise argparse.ArgumentTypeError("down payment must be between 0 and 100%")
    return x


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Cap-rate sensitivity: NOI = price × assumed cap; "
        "LTV from loan sizing; CoC and DSCR from year-one cash flow.",
    )
    p.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run guided prompts (questionary) instead of command-line flags",
    )
    p.add_argument(
        "--price",
        type=_positive_money,
        default=None,
        help='Purchase price (e.g. 2700000, "2.7M", "874k"); required unless --interactive',
    )
    p.add_argument(
        "--listing-cap",
        type=_positive_percent,
        default=None,
        help="Listing / center cap as a display percent (e.g. 6.25 for 6.25%%); required for batch mode",
    )
    p.add_argument(
        "--down",
        type=_fraction,
        default=None,
        help="Down payment (e.g. 25 or 0.25); required for non-interactive runs",
    )
    p.add_argument(
        "--rate",
        type=_positive_percent,
        default=None,
        help="Loan rate as a display percent (e.g. 6.75 for 6.75%%); required for batch mode",
    )
    p.add_argument(
        "--amort",
        type=int,
        default=None,
        help="Amortization in years; required for non-interactive runs",
    )
    p.add_argument(
        "--balloon",
        type=int,
        default=None,
        help="Balloon / maturity in years; required for non-interactive runs",
    )
    p.add_argument(
        "--sweep-step",
        type=_positive_percent,
        default=_DEFAULT_SWEEP_STEP,
        help="Cap sweep step as a display percent per band (default 0.1 i.e. 0.1%% = 10 bps)",
    )
    p.add_argument("--sweep-below", type=int, default=0, help="Steps below listing cap")
    p.add_argument("--sweep-above", type=int, default=15, help="Steps above listing cap")
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.interactive:
        from cre_calcs.wizard import run_wizard

        run_wizard()
        return
    missing = [
        name
        for name, val in (
            ("--price", args.price),
            ("--listing-cap", args.listing_cap),
            ("--down", args.down),
            ("--rate", args.rate),
            ("--amort", args.amort),
            ("--balloon", args.balloon),
        )
        if val is None
    ]
    if missing:
        parser.error(
            "the following arguments are required for batch mode: "
            + ", ".join(missing)
            + " (or use --interactive)"
        )
    listing = Listing(
        purchase_price=args.price,
        listing_cap_rate=args.listing_cap,
    )
    loan = LoanTerms(
        down_payment_fraction=args.down,
        annual_interest_rate=args.rate,
        amortization_years=args.amort,
        balloon_years=args.balloon,
    )
    sweep = CapRateSweep(
        center_cap_rate=args.listing_cap,
        step=args.sweep_step,
        steps_below=args.sweep_below,
        steps_above=args.sweep_above,
    )
    rows = build_cap_rate_scenarios(listing, loan, sweep)
    print(format_scenario_table(listing, loan, rows))


if __name__ == "__main__":
    main()
