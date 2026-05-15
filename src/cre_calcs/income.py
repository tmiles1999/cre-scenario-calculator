"""Operating income from stated NOI with optional escalation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EscalatorStepUnit(str, Enum):
    """Calendar spacing between step increases (analysis uses 12-month years)."""

    YEARS = "yrs"
    MONTHS = "mo"


class EscalatorIncreaseKind(str, Enum):
    """Each completed step applies a multiplicative percent or additive dollars."""

    PERCENT = "percent"
    DOLLARS = "dollars"


@dataclass(frozen=True, slots=True)
class StepEscalator:
    """Step up income every ``every_n`` whole years or months (from start of year 1).

    Completed steps before analysis year ``Y`` use elapsed time ``(Y-1) × 12`` months
    divided by the period length in months (``every_n`` years ⇒ ``every_n × 12`` months).
    """

    every_n: int
    unit: EscalatorStepUnit
    kind: EscalatorIncreaseKind
    amount: float

    def __post_init__(self) -> None:
        if self.every_n < 1:
            raise ValueError("every_n must be at least 1")
        if self.amount < 0:
            raise ValueError("amount cannot be negative")

    def period_months(self) -> float:
        if self.unit is EscalatorStepUnit.YEARS:
            return float(self.every_n * 12)
        return float(self.every_n)

    def steps_completed_before_year(self, year: int) -> int:
        """How many full periods have elapsed before the start of ``year`` (1-based)."""
        if year < 1:
            raise ValueError("year must be >= 1")
        elapsed_months = (year - 1) * 12
        period = self.period_months()
        if period <= 0:
            raise ValueError("period must be positive")
        return int(elapsed_months // period)


@dataclass(frozen=True, slots=True)
class StatedNoi:
    """Direct year-1 NOI with optional uniform annual escalation or step escalator."""

    year1_noi: float
    annual_escalator_fraction: float = 0.0
    step_escalator: StepEscalator | None = None

    def __post_init__(self) -> None:
        if self.year1_noi < 0:
            raise ValueError("year1_noi cannot be negative")
        if self.annual_escalator_fraction < 0:
            raise ValueError("annual_escalator_fraction cannot be negative")
        if self.step_escalator is not None and self.annual_escalator_fraction != 0.0:
            raise ValueError("set either annual_escalator_fraction or step_escalator, not both")

    def operating_income_year(self, year: int) -> float:
        if year < 1:
            raise ValueError("year must be >= 1")
        if self.step_escalator is not None:
            s = self.step_escalator
            k = s.steps_completed_before_year(year)
            if k <= 0:
                return self.year1_noi
            if s.kind is EscalatorIncreaseKind.PERCENT:
                return self.year1_noi * (1.0 + s.amount) ** k
            return self.year1_noi + s.amount * float(k)
        return self.year1_noi * (1.0 + self.annual_escalator_fraction) ** (year - 1)
