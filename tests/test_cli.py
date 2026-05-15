"""CLI argument parsing."""

import pytest

from cre_calcs.cli import build_parser, main


def test_interactive_parses_without_batch_flags() -> None:
    args = build_parser().parse_args(["--interactive"])
    assert args.interactive is True
    assert args.price is None
    assert args.listing_cap is None


def test_batch_main_errors_when_loan_fields_missing() -> None:
    with pytest.raises(SystemExit):
        main(["--price", "1m", "--listing-cap", "0.06"])


def test_cli_accepts_price_shorthand_m_and_k() -> None:
    args = build_parser().parse_args(
        [
            "--price",
            "2.7M",
            "--listing-cap",
            "6.5",
            "--down",
            "25",
            "--rate",
            "6",
            "--amort",
            "30",
            "--balloon",
            "10",
        ]
    )
    assert args.price == 2_700_000.0
    assert args.listing_cap == 0.065
    assert args.rate == 0.06


def test_cli_accepts_dollar_signs_and_commas_in_price() -> None:
    args = build_parser().parse_args(
        [
            "--price",
            "$2,700,000",
            "--listing-cap",
            "6.5%",
            "--down",
            "0.25",
            "--rate",
            "6",
            "--amort",
            "30",
            "--balloon",
            "10",
        ]
    )
    assert args.price == 2_700_000.0
    assert args.listing_cap == 0.065
    assert args.rate == 0.06


def test_cli_cap_and_rates_are_display_percent_only() -> None:
    """0.1 means 0.1% cap, not 10%; 6.25% suffix allowed."""
    args = build_parser().parse_args(
        [
            "--price",
            "1M",
            "--listing-cap",
            "0.1",
            "--down",
            "25",
            "--rate",
            "6.5",
            "--amort",
            "30",
            "--balloon",
            "10",
            "--sweep-step",
            "0.1",
            "--sweep-below",
            "0",
            "--sweep-above",
            "0",
        ]
    )
    assert args.listing_cap == 0.001
    assert args.rate == 0.065
    assert args.sweep_step == 0.001
