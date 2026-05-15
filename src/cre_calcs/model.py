"""Immutable inputs for listing and financing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Listing:
    """Commercial listing at a negotiated or asking purchase price."""

    purchase_price: float
    listing_cap_rate: float
    percentage_rent_annual: float = 0.0

    def __post_init__(self) -> None:
        if self.purchase_price <= 0:
            raise ValueError("purchase_price must be positive")
        if self.listing_cap_rate <= 0:
            raise ValueError("listing_cap_rate must be positive")
        if self.percentage_rent_annual < 0:
            raise ValueError("percentage_rent_annual cannot be negative")

    def net_operating_income_at_cap(self, assumed_cap_rate: float) -> float:
        """NOI implied by holding price fixed and applying an assumed cap.

        NOI = Price × Cap + optional percentage-rent increment (annual $).
        """
        if assumed_cap_rate <= 0:
            raise ValueError("assumed_cap_rate must be positive")
        return self.purchase_price * assumed_cap_rate + self.percentage_rent_annual


@dataclass(frozen=True, slots=True)
class LoanTerms:
    """Fixed-rate amortizing loan; balloon is informational for exit, not cash flow year 1."""

    down_payment_fraction: float
    annual_interest_rate: float
    amortization_years: int
    balloon_years: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.down_payment_fraction <= 1.0:
            raise ValueError("down_payment_fraction must be between 0 and 1")
        if self.annual_interest_rate <= 0:
            raise ValueError("annual_interest_rate must be positive")
        if self.amortization_years <= 0:
            raise ValueError("amortization_years must be positive")
        if self.balloon_years <= 0:
            raise ValueError("balloon_years must be positive")


@dataclass(frozen=True, slots=True)
class CapRateSweep:
    """Arithmetic sweep around a center cap rate (e.g. ±25 bps)."""

    center_cap_rate: float
    step: float
    steps_below: int
    steps_above: int

    def __post_init__(self) -> None:
        if self.center_cap_rate <= 0:
            raise ValueError("center_cap_rate must be positive")
        if self.step <= 0:
            raise ValueError("step must be positive")
        if self.steps_below < 0 or self.steps_above < 0:
            raise ValueError("steps must be non-negative")

    def cap_rates_low_to_high(self) -> tuple[float, ...]:
        """Cap rates in ascending order; values at or below zero are dropped.

        Wide sweeps (large step × many steps) can push the arithmetic grid below
        zero; those bands are invalid for implied-price math (NOI ÷ cap).
        """
        start = self.center_cap_rate - self.step * self.steps_below
        n = 1 + self.steps_below + self.steps_above
        raw = tuple(start + self.step * i for i in range(n))
        positive = tuple(c for c in raw if c > 0.0)
        if not positive:
            raise ValueError("cap sweep produced no positive cap rates")
        return positive


@dataclass(frozen=True, slots=True)
class LoanRateTerms:
    """Interest and amortization; paired with a down payment to form ``LoanTerms``."""

    annual_interest_rate: float
    amortization_years: int
    balloon_years: int

    def __post_init__(self) -> None:
        if self.annual_interest_rate <= 0:
            raise ValueError("annual_interest_rate must be positive")
        if self.amortization_years <= 0:
            raise ValueError("amortization_years must be positive")
        if self.balloon_years <= 0:
            raise ValueError("balloon_years must be positive")

    def with_down_payment(self, down_payment_fraction: float) -> LoanTerms:
        return LoanTerms(
            down_payment_fraction=down_payment_fraction,
            annual_interest_rate=self.annual_interest_rate,
            amortization_years=self.amortization_years,
            balloon_years=self.balloon_years,
        )


@dataclass(frozen=True, slots=True)
class DownPaymentSweep:
    """Arithmetic sweep of equity contribution (as a fraction of purchase price)."""

    center_down_payment_fraction: float
    step: float
    steps_below: int
    steps_above: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.center_down_payment_fraction <= 1.0:
            raise ValueError("center_down_payment_fraction must be between 0 and 1")
        if self.step <= 0:
            raise ValueError("step must be positive")
        if self.steps_below < 0 or self.steps_above < 0:
            raise ValueError("steps must be non-negative")

    def down_payment_fractions_low_to_high(self) -> tuple[float, ...]:
        start = self.center_down_payment_fraction - self.step * self.steps_below
        n = 1 + self.steps_below + self.steps_above
        values: list[float] = []
        for i in range(n):
            d = start + self.step * i
            if 0.0 <= d <= 1.0:
                values.append(d)
        return tuple(values)
