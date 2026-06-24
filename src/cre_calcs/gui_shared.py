"""Streamlit GUI helpers with no Streamlit import (safe for unit tests).

Widget key helpers keep shared sidebar inputs aligned with tests and avoid
accidentally diverging keys across tabs.
"""

from __future__ import annotations

# Prefixes for session-state keys (single render site in the GUI).
SHARED_LOAN_WIDGET_KEY_PREFIX = "shared_loan"
SHARED_CAP_SWEEP_WIDGET_KEY_PREFIX = "shared_cap_sweep"

# Single render site: cap fixed, implied price, down sweep (where applicable).
SHARED_PURCHASE_PRICE_KEY = "shared_purchase_price"
SHARED_LOAN_DOWN_PCT_KEY = "shared_loan_down_pct"
SHARED_OPERATING_NOI_RAW_KEY = "shared_operating_noi_raw"

# Implied Price tab: NOI growth and analysis year (single render site).
IMPLIED_ESC_MODEL_KEY = "implied_esc_model"
IMPLIED_ESC_PCT_KEY = "implied_esc_pct"
IMPLIED_STEP_EVERY_KEY = "implied_step_every"
IMPLIED_STEP_UNIT_KEY = "implied_step_unit"
IMPLIED_STEP_KIND_KEY = "implied_step_kind"
IMPLIED_STEP_AMT_PCT_KEY = "implied_step_amt_pct"
IMPLIED_STEP_AMT_MONEY_KEY = "implied_step_amt_money"
IMPLIED_PROJECTION_HORIZON_KEY = "implied_projection_horizon"


def shared_deal_assumption_keys() -> tuple[str, ...]:
    """Stable keys for linked sidebar fields (must be unique vs loan/cap sweep keys)."""
    return (
        SHARED_PURCHASE_PRICE_KEY,
        SHARED_LOAN_DOWN_PCT_KEY,
        SHARED_OPERATING_NOI_RAW_KEY,
    )


def loan_input_widget_keys(prefix: str = SHARED_LOAN_WIDGET_KEY_PREFIX) -> tuple[str, str, str]:
    """Keys for loan rate %, amortization years, balloon years (must be unique)."""
    return (
        f"{prefix}_loan_rate_pct",
        f"{prefix}_amort_years",
        f"{prefix}_balloon_years",
    )


def cap_sweep_widget_keys(prefix: str = SHARED_CAP_SWEEP_WIDGET_KEY_PREFIX) -> tuple[str, str, str, str]:
    """Keys for cap sweep center, step, steps below, steps above."""
    return (
        f"{prefix}_sweep_center_cap_pct",
        f"{prefix}_sweep_cap_step_pct",
        f"{prefix}_sweep_steps_below",
        f"{prefix}_sweep_steps_above",
    )


def implied_escalator_widget_keys() -> tuple[str, ...]:
    """Keys for implied-price NOI growth and projection horizon."""
    return (
        IMPLIED_ESC_MODEL_KEY,
        IMPLIED_ESC_PCT_KEY,
        IMPLIED_STEP_EVERY_KEY,
        IMPLIED_STEP_UNIT_KEY,
        IMPLIED_STEP_KIND_KEY,
        IMPLIED_STEP_AMT_PCT_KEY,
        IMPLIED_STEP_AMT_MONEY_KEY,
        IMPLIED_PROJECTION_HORIZON_KEY,
    )
