"""Streamlit GUI: live scenario table and PDF export."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from cre_calcs.gui_shared import (
    SHARED_CAP_SWEEP_WIDGET_KEY_PREFIX,
    SHARED_LISTING_CAP_PCT_KEY,
    SHARED_LOAN_DOWN_PCT_KEY,
    SHARED_LOAN_WIDGET_KEY_PREFIX,
    SHARED_OPERATING_NOI_RAW_KEY,
    SHARED_PURCHASE_PRICE_KEY,
    cap_sweep_widget_keys,
    loan_input_widget_keys,
)
from cre_calcs.income import (
    EscalatorIncreaseKind,
    EscalatorStepUnit,
    StatedNoi,
    StepEscalator,
)
from cre_calcs.model import CapRateSweep, DownPaymentSweep, Listing, LoanRateTerms, LoanTerms
from cre_calcs.money_parse import parse_money_amount
from cre_calcs.scenarios import (
    ScenarioRow,
    build_cap_implied_price_scenarios,
    build_cap_rate_scenarios,
    build_down_payment_scenarios,
)
from cre_calcs.table import balloon_snapshot_line, scenario_rows_matrix

st.set_page_config(page_title="CRE Scenarios", layout="wide", initial_sidebar_state="expanded")


def _pct(x: float) -> float:
    """Display percent (e.g. 6.25) to decimal rate."""
    return x / 100.0


def _sidebar_label_field() -> tuple[object, object]:
    """Narrow label column + field column for a single sidebar row."""
    return st.columns([2, 3])


def _maybe_step_escalator(
    *,
    use_annual: bool,
    step_every: int,
    step_unit: str,
    step_kind: str,
    step_amt_pct: float,
    step_amt_money_raw: str,
) -> StepEscalator | None:
    """Build step escalator when UI is in step mode; ``use_annual`` skips step math."""
    if use_annual:
        return None
    unit_e = EscalatorStepUnit.YEARS if step_unit == "yrs" else EscalatorStepUnit.MONTHS
    kind_e = EscalatorIncreaseKind.PERCENT if step_kind == "%" else EscalatorIncreaseKind.DOLLARS
    if kind_e is EscalatorIncreaseKind.PERCENT:
        amt = _pct(step_amt_pct)
    else:
        amt = parse_money_amount(step_amt_money_raw)
    return StepEscalator(
        every_n=int(step_every),
        unit=unit_e,
        kind=kind_e,
        amount=float(amt),
    )


def _loan_inputs(*, label_prefix: str = "", key_prefix: str) -> tuple[float, int, int]:
    k_rate, k_amort, k_balloon = loan_input_widget_keys(key_prefix)
    lr, rr = _sidebar_label_field()
    with lr:
        st.caption(f"{label_prefix}Loan Rate (%)")
    with rr:
        rate_pct = st.number_input(
            "loan_rate_pct",
            label_visibility="collapsed",
            min_value=0.01,
            max_value=30.0,
            value=6.5,
            step=0.05,
            format="%.4f",
            help="Annual interest as a display percent (6.5 = 6.5%).",
            key=k_rate,
        )
    la, ra = _sidebar_label_field()
    with la:
        st.caption(f"{label_prefix}Amortization (Yr)")
    with ra:
        amort = st.number_input(
            "amort_years",
            label_visibility="collapsed",
            min_value=1,
            max_value=40,
            value=25,
            key=k_amort,
        )
    lb, rb = _sidebar_label_field()
    with lb:
        st.caption(f"{label_prefix}Balloon (Yr)")
    with rb:
        balloon = st.number_input(
            "balloon_years",
            label_visibility="collapsed",
            min_value=1,
            max_value=40,
            value=10,
            key=k_balloon,
        )
    return _pct(rate_pct), int(amort), int(balloon)


def _sweep_cap_inputs(*, label_prefix: str = "", key_prefix: str) -> CapRateSweep:
    k_center, k_step, k_below, k_above = cap_sweep_widget_keys(key_prefix)
    lc, rc = _sidebar_label_field()
    with lc:
        st.caption(f"{label_prefix}Center Cap (%)")
    with rc:
        center = st.number_input(
            "sweep_center_cap",
            label_visibility="collapsed",
            min_value=0.01,
            max_value=50.0,
            value=6.0,
            step=0.1,
            format="%.4f",
            key=k_center,
        )
    ls, rs = _sidebar_label_field()
    with ls:
        st.caption(f"{label_prefix}Cap Step (%)")
    with rs:
        step = st.number_input(
            "sweep_cap_step",
            label_visibility="collapsed",
            min_value=0.01,
            max_value=10.0,
            value=0.1,
            step=0.1,
            format="%.4f",
            help="Per row, in display percent (0.1 = 0.1% = 10 bps).",
            key=k_step,
        )
    lb, rb = _sidebar_label_field()
    with lb:
        st.caption(f"{label_prefix}Steps Below")
    with rb:
        below = st.number_input(
            "sweep_steps_below",
            label_visibility="collapsed",
            min_value=0,
            max_value=50,
            value=0,
            key=k_below,
        )
    la, ra = _sidebar_label_field()
    with la:
        st.caption(f"{label_prefix}Steps Above")
    with ra:
        above = st.number_input(
            "sweep_steps_above",
            label_visibility="collapsed",
            min_value=0,
            max_value=50,
            value=15,
            key=k_above,
        )
    return CapRateSweep(
        center_cap_rate=_pct(center),
        step=_pct(step),
        steps_below=int(below),
        steps_above=int(above),
    )


def _render_table_and_pdf(
    rows: list[ScenarioRow],
    summary_lines: list[str],
    *,
    balloon_price: float | None,
    balloon_loan: LoanTerms | None,
    pdf_title: str,
    download_button_key: str,
    pdf_footer: list[str] | None = None,
) -> None:
    st.subheader("Scenario Results")
    for line in summary_lines:
        st.caption(line)
    if balloon_price is not None and balloon_loan is not None:
        st.caption(balloon_snapshot_line(balloon_price, balloon_loan))

    headers, matrix = scenario_rows_matrix(rows)
    st.dataframe(pd.DataFrame(matrix, columns=headers), use_container_width=True, hide_index=True)

    extra_summary = list(summary_lines)
    if balloon_price is not None and balloon_loan is not None:
        extra_summary.append(balloon_snapshot_line(balloon_price, balloon_loan))

    from cre_calcs.pdf_report import build_scenario_pdf

    pdf = build_scenario_pdf(
        title=pdf_title,
        summary_lines=extra_summary,
        headers=headers,
        rows=matrix,
        footer_lines=pdf_footer
        or [
            "Figures are illustrative. NOI, expenses, and financing should be confirmed with "
            "qualified professionals before making investment decisions.",
        ],
    )
    st.download_button(
        label="Download PDF Report",
        data=pdf,
        file_name="cre_scenario_analysis.pdf",
        mime="application/pdf",
        type="primary",
        key=download_button_key,
    )


def tab_cap_fixed(
    rate: float,
    amort: int,
    balloon: int,
    sweep: CapRateSweep,
    *,
    price_raw: str,
    listing_cap_pct: float,
    loan_down_pct: float,
) -> None:
    st.subheader("Cap Rate Sweep at a Fixed Purchase Price")
    st.caption(
        "NOI = purchase price × each row’s assumed going-in cap. "
        "Purchase price, listing cap, and loan down % are in the sidebar (shared)."
    )

    try:
        price = parse_money_amount(price_raw)
        listing = Listing(
            purchase_price=price,
            listing_cap_rate=_pct(listing_cap_pct),
        )
        loan = LoanTerms(
            down_payment_fraction=_pct(loan_down_pct),
            annual_interest_rate=rate,
            amortization_years=amort,
            balloon_years=balloon,
        )
        rows = build_cap_rate_scenarios(listing, loan, sweep)
        summary = [
            f"Purchase ${listing.purchase_price:,.0f}; listing cap {listing_cap_pct:.4f}%; "
            f"loan {rate:.4%} {amort}yr/{balloon}yr balloon; down {loan_down_pct:.2f}%."
        ]
        _render_table_and_pdf(
            rows,
            summary,
            balloon_price=listing.purchase_price,
            balloon_loan=loan,
            pdf_title="CRE Analysis — Cap Sweep (Fixed Price)",
            download_button_key="pdf_dl_cap_fixed",
        )
    except ValueError as e:
        st.error(str(e))


def tab_implied_price(
    rate: float,
    amort: int,
    balloon: int,
    sweep: CapRateSweep,
    *,
    loan_down_pct: float,
    operating_noi_raw: str,
) -> None:
    st.subheader("Cap Sweep to Implied Purchase Price")
    st.caption(
        "Stated NOI (from sidebar) ÷ cap = implied price; loan sized off each implied price. "
        "Loan down % is in the sidebar (shared with Cap at Fixed Price)."
    )

    with st.container():
        esc_model = st.radio(
            "NOI Growth",
            ["Annual (Compound Each Year)", "Step on a Schedule"],
            horizontal=True,
            key="implied_esc_model",
        )
        annual_esc = esc_model.startswith("Annual")
        esc_pct = st.number_input(
            "Annual Escalator (%/yr, 0 if None)",
            value=0.0,
            step=0.1,
            format="%.4f",
            key="implied_esc_pct",
            disabled=not annual_esc,
            help="Applied every analysis year (display %, e.g. 3 = 3%).",
        )
        st.caption("Step Schedule (when not using annual compound)")
        c_step = st.columns([1, 1, 1, 2])
        with c_step[0]:
            step_every = st.number_input(
                "Every",
                min_value=1,
                max_value=120,
                value=1,
                step=1,
                key="implied_step_every",
                disabled=annual_esc,
            )
        with c_step[1]:
            step_unit = st.selectbox(
                "Period Unit",
                ["yrs", "mo"],
                index=0,
                key="implied_step_unit",
                disabled=annual_esc,
            )
        with c_step[2]:
            step_kind = st.selectbox(
                "Increase Type",
                ["%", "$"],
                index=0,
                key="implied_step_kind",
                disabled=annual_esc,
            )
        with c_step[3]:
            step_amt_pct = st.number_input(
                "Increase (%/Step)",
                value=3.0,
                step=0.1,
                format="%.4f",
                key="implied_step_amt_pct",
                disabled=annual_esc or step_kind != "%",
                help="Display percent per completed period (e.g. 3 = 3%).",
            )
            step_amt_money = st.text_input(
                "Increase ($/Step)",
                value="1000",
                key="implied_step_amt_money",
                disabled=annual_esc or step_kind != "$",
                help="Dollar bump per completed period (e.g. 1k, 2500).",
            )
        analysis_year = st.number_input(
            "Analysis Year",
            min_value=1,
            max_value=30,
            value=1,
            key="implied_analysis_year",
        )

    try:
        y1 = parse_money_amount(operating_noi_raw)
        step = _maybe_step_escalator(
            use_annual=annual_esc,
            step_every=int(step_every),
            step_unit=str(step_unit),
            step_kind=str(step_kind),
            step_amt_pct=float(step_amt_pct),
            step_amt_money_raw=step_amt_money,
        )
        if annual_esc:
            stated_noi = StatedNoi(year1_noi=y1, annual_escalator_fraction=_pct(esc_pct))
        else:
            stated_noi = StatedNoi(year1_noi=y1, annual_escalator_fraction=0.0, step_escalator=step)
        noi = stated_noi.operating_income_year(int(analysis_year))
    except ValueError as e:
        st.error(str(e))
        return

    try:
        rates = LoanRateTerms(rate, amort, balloon)
        rows = build_cap_implied_price_scenarios(
            operating_income=noi,
            down_payment_fraction=_pct(loan_down_pct),
            loan_rates=rates,
            cap_sweep=sweep,
        )
        loan = rates.with_down_payment(_pct(loan_down_pct))
        cc = sweep.center_cap_rate
        ref_p = noi / cc if cc else 0.0
        summary = [
            f"Operating income (analysis year {int(analysis_year)}): ${noi:,.0f} "
            f"— same for every cap row (shown here only; omitted from the table).",
            f"Down {loan_down_pct:.2f}%; loan {rate:.4%} {amort}yr/{balloon}yr balloon; "
            f"reference price @ center cap ≈ ${ref_p:,.0f}.",
        ]
        _render_table_and_pdf(
            rows,
            summary,
            balloon_price=ref_p,
            balloon_loan=loan,
            pdf_title="CRE Analysis — Implied Price (Cap on NOI)",
            download_button_key="pdf_dl_implied",
        )
    except ValueError as e:
        st.error(str(e))


def tab_down_sweep(
    rate: float,
    amort: int,
    balloon: int,
    *,
    price_raw: str,
    operating_noi_raw: str,
    listing_cap_pct: float,
) -> None:
    st.subheader("Down Payment Sweep")
    st.caption(
        "Fixed price and NOI; LTV and cash-on-cash move with equity. "
        "Purchase price, operating NOI, and reference cap are in the sidebar (shared)."
    )

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        d_center = st.number_input("Center Down (%)", value=35.0, step=1.0, format="%.2f")
    with c6:
        d_step = st.number_input("Down Step (%)", value=5.0, step=1.0, format="%.2f")
    with c7:
        d_below = st.number_input("Steps Below", min_value=0, max_value=20, value=2, key="ds_b")
    with c8:
        d_above = st.number_input("Steps Above", min_value=0, max_value=20, value=2, key="ds_a")

    try:
        price = parse_money_amount(price_raw)
        noi = parse_money_amount(operating_noi_raw)
        rates = LoanRateTerms(rate, amort, balloon)
        sweep = DownPaymentSweep(
            center_down_payment_fraction=_pct(d_center),
            step=_pct(d_step),
            steps_below=int(d_below),
            steps_above=int(d_above),
        )
        rows = build_down_payment_scenarios(
            purchase_price=price,
            operating_income=noi,
            listing_cap_for_display=_pct(listing_cap_pct),
            loan_rates=rates,
            sweep=sweep,
        )
        loan = rates.with_down_payment(sweep.center_down_payment_fraction)
        summary = [
            f"Price ${price:,.0f}; NOI ${noi:,.0f}/yr; ref. cap {listing_cap_pct:.4f}%; "
            f"loan {rate:.4%} {amort}yr/{balloon}yr."
        ]
        _render_table_and_pdf(
            rows,
            summary,
            balloon_price=price,
            balloon_loan=loan,
            pdf_title="CRE Analysis — Down Payment Sweep",
            download_button_key="pdf_dl_down_sweep",
        )
    except ValueError as e:
        st.error(str(e))


def main() -> None:
    st.title("Commercial Real Estate Scenarios")
    st.markdown(
        "Caps, loan rate, and sweep steps use **display percents** (6.25 = 6.25%). "
        "Down payment uses **display percent of price** (25 = 25% equity)."
    )

    with st.sidebar:
        st.header("Mortgage Terms (All Tabs)")
        st.caption(
            "Interest rate, amortization, and balloon maturity—used everywhere "
            "the model sizes annual debt service and LTV."
        )
        rate, amort, balloon = _loan_inputs(
            label_prefix="",
            key_prefix=SHARED_LOAN_WIDGET_KEY_PREFIX,
        )
        st.divider()
        st.subheader("Going-In Cap Grid (Two Cap Tabs)")
        st.caption(
            "Center cap, step size, and how many rows below/above center. "
            "Each scenario row is one going-in cap—on **Implied Price** (purchase price moves with cap) "
            "and **Cap at Fixed Price** (NOI moves with cap). "
            "Not used on **Down Payment**."
        )
        sweep = _sweep_cap_inputs(
            label_prefix="",
            key_prefix=SHARED_CAP_SWEEP_WIDGET_KEY_PREFIX,
        )
        st.divider()
        st.subheader("Deal: Price, Income, Caps, Loan Down")
        st.caption(
            "**Implied Price:** Y1 / operating NOI and loan down % (price = NOI ÷ row cap). "
            "**Down Payment:** same price and NOI; listing cap is a display reference only—"
            "that tab’s down % grid replaces sidebar loan down for sizing. "
            "**Cap at Fixed Price:** purchase price, listing cap, and loan down % "
            "(NOI = price × row cap)."
        )
        lp, rp = _sidebar_label_field()
        with lp:
            st.caption("Purchase Price")
        with rp:
            price_raw = st.text_input(
                "purchase_price",
                value="3.2M",
                label_visibility="collapsed",
                help="e.g. 3.2M, 874k — fixed-price cap & down sweep.",
                key=SHARED_PURCHASE_PRICE_KEY,
            )
        ll, rl = _sidebar_label_field()
        with ll:
            st.caption("List / Ref Cap (%)")
        with rl:
            listing_cap_pct = st.number_input(
                "listing_ref_cap_pct",
                label_visibility="collapsed",
                value=6.0,
                step=0.1,
                format="%.4f",
                key=SHARED_LISTING_CAP_PCT_KEY,
                help="Listing cap for fixed-price tab; reference cap for down sweep.",
            )
        ld, rd = _sidebar_label_field()
        with ld:
            st.caption("Down Payment (%)")
        with rd:
            loan_down_pct = st.number_input(
                "loan_down_pct",
                label_visibility="collapsed",
                min_value=0.0,
                max_value=100.0,
                value=25.0,
                step=1.0,
                format="%.2f",
                key=SHARED_LOAN_DOWN_PCT_KEY,
                help="Equity share for loan sizing on Cap at Fixed Price and Implied Price tabs.",
            )
        lo, ro = _sidebar_label_field()
        with lo:
            st.caption("Year 1 / Operating NOI ($)")
        with ro:
            operating_noi_raw = st.text_input(
                "operating_noi",
                value="155k",
                label_visibility="collapsed",
                key=SHARED_OPERATING_NOI_RAW_KEY,
                help="Implied tab (stated Y1) and down sweep (annual NOI).",
            )

    tab1, tab2, tab3 = st.tabs(["Implied Price", "Down Payment", "Cap at Fixed Price"])
    with tab1:
        tab_implied_price(
            rate,
            amort,
            balloon,
            sweep,
            loan_down_pct=loan_down_pct,
            operating_noi_raw=operating_noi_raw,
        )
    with tab2:
        tab_down_sweep(
            rate,
            amort,
            balloon,
            price_raw=price_raw,
            operating_noi_raw=operating_noi_raw,
            listing_cap_pct=listing_cap_pct,
        )
    with tab3:
        tab_cap_fixed(
            rate,
            amort,
            balloon,
            sweep,
            price_raw=price_raw,
            listing_cap_pct=listing_cap_pct,
            loan_down_pct=loan_down_pct,
        )


if __name__ == "__main__":
    main()
