"""Contract tests for Streamlit widget keys used by the shared sidebar."""

from cre_calcs.gui_shared import (
    SHARED_CAP_SWEEP_WIDGET_KEY_PREFIX,
    SHARED_LOAN_WIDGET_KEY_PREFIX,
    cap_sweep_widget_keys,
    implied_escalator_widget_keys,
    loan_input_widget_keys,
    shared_deal_assumption_keys,
)


def test_loan_widget_keys_are_unique_and_prefixed() -> None:
    keys = loan_input_widget_keys()
    assert len(keys) == 3
    assert len(set(keys)) == 3
    for k in keys:
        assert k.startswith(SHARED_LOAN_WIDGET_KEY_PREFIX)


def test_cap_sweep_widget_keys_are_unique_and_prefixed() -> None:
    keys = cap_sweep_widget_keys()
    assert len(keys) == 4
    assert len(set(keys)) == 4
    for k in keys:
        assert k.startswith(SHARED_CAP_SWEEP_WIDGET_KEY_PREFIX)


def test_custom_prefixes_do_not_collide_with_defaults() -> None:
    loan_custom = loan_input_widget_keys("tab_cap")
    cap_custom = cap_sweep_widget_keys("tab_cap")
    assert set(loan_custom).isdisjoint(cap_custom)
    assert set(loan_custom).isdisjoint(loan_input_widget_keys())
    assert set(cap_custom).isdisjoint(cap_sweep_widget_keys())


def test_shared_deal_keys_disjoint_from_loan_and_cap_keys() -> None:
    deal = set(shared_deal_assumption_keys())
    loan = set(loan_input_widget_keys())
    cap = set(cap_sweep_widget_keys())
    assert deal.isdisjoint(loan)
    assert deal.isdisjoint(cap)
    assert len(deal) == 3


def test_implied_escalator_widget_keys_are_unique() -> None:
    keys = implied_escalator_widget_keys()
    assert len(keys) == 8
    assert len(set(keys)) == 8
    assert set(keys).isdisjoint(loan_input_widget_keys())
    assert set(keys).isdisjoint(cap_sweep_widget_keys())
    assert set(keys).isdisjoint(shared_deal_assumption_keys())
