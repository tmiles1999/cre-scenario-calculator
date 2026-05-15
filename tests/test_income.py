"""Stated NOI schedules and step escalators."""

import math

import pytest

from cre_calcs.income import (
    EscalatorIncreaseKind,
    EscalatorStepUnit,
    StatedNoi,
    StepEscalator,
)


def test_stated_noi_with_escalator() -> None:
    s = StatedNoi(year1_noi=500_000.0, annual_escalator_fraction=0.03)
    assert math.isclose(s.operating_income_year(1), 500_000.0)
    assert math.isclose(s.operating_income_year(2), 515_000.0)


def test_stated_noi_rejects_negative_year1() -> None:
    with pytest.raises(ValueError, match="year1_noi"):
        StatedNoi(year1_noi=-1, annual_escalator_fraction=0.0)


def test_step_escalator_rejects_non_positive_every_n() -> None:
    with pytest.raises(ValueError, match="every_n"):
        StepEscalator(0, EscalatorStepUnit.YEARS, EscalatorIncreaseKind.DOLLARS, 1_000.0)


def test_stated_noi_dollar_step_every_three_years() -> None:
    """$1k bump each time 3 full years elapse before analysis year."""
    s = StatedNoi(
        year1_noi=100_000.0,
        annual_escalator_fraction=0.0,
        step_escalator=StepEscalator(
            every_n=3,
            unit=EscalatorStepUnit.YEARS,
            kind=EscalatorIncreaseKind.DOLLARS,
            amount=1_000.0,
        ),
    )
    assert math.isclose(s.operating_income_year(1), 100_000.0)
    assert math.isclose(s.operating_income_year(3), 100_000.0)
    assert math.isclose(s.operating_income_year(4), 101_000.0)
    assert math.isclose(s.operating_income_year(6), 101_000.0)
    assert math.isclose(s.operating_income_year(7), 102_000.0)


def test_stated_percent_step_every_eighteen_months() -> None:
    """3% per step on stated NOI; first step after 24 months → year 3."""
    s = StatedNoi(
        year1_noi=120_000.0,
        annual_escalator_fraction=0.0,
        step_escalator=StepEscalator(
            every_n=18,
            unit=EscalatorStepUnit.MONTHS,
            kind=EscalatorIncreaseKind.PERCENT,
            amount=0.03,
        ),
    )
    assert math.isclose(s.operating_income_year(1), 120_000.0)
    assert math.isclose(s.operating_income_year(2), 120_000.0)
    assert math.isclose(s.operating_income_year(3), 120_000.0 * 1.03)


def test_annual_compound_matches_one_year_percent_step_stated() -> None:
    annual = StatedNoi(year1_noi=200_000.0, annual_escalator_fraction=0.10)
    stepped = StatedNoi(
        year1_noi=200_000.0,
        annual_escalator_fraction=0.0,
        step_escalator=StepEscalator(
            1,
            EscalatorStepUnit.YEARS,
            EscalatorIncreaseKind.PERCENT,
            0.10,
        ),
    )
    for y in (1, 2, 3, 5):
        assert math.isclose(
            annual.operating_income_year(y),
            stepped.operating_income_year(y),
            rel_tol=1e-12,
        )


def test_stated_cannot_set_both_annual_fraction_and_step() -> None:
    with pytest.raises(ValueError, match="not both"):
        StatedNoi(
            year1_noi=50_000.0,
            annual_escalator_fraction=0.02,
            step_escalator=StepEscalator(
                1, EscalatorStepUnit.YEARS, EscalatorIncreaseKind.DOLLARS, 100.0
            ),
        )
