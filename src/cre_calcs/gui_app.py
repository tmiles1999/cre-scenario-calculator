"""Streamlit GUI: live scenario table and PDF export."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from cre_calcs.gui_shared import (
    IMPLIED_ESC_MODEL_KEY,
    IMPLIED_ESC_PCT_KEY,
    IMPLIED_PROJECTION_HORIZON_KEY,
    IMPLIED_STEP_AMT_MONEY_KEY,
    IMPLIED_STEP_AMT_PCT_KEY,
    IMPLIED_STEP_EVERY_KEY,
    IMPLIED_STEP_KIND_KEY,
    IMPLIED_STEP_UNIT_KEY,
    SHARED_CAP_SWEEP_WIDGET_KEY_PREFIX,
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
    build_year_projection,
    inject_offer_cap_row,
)
from cre_calcs.table import (
    balloon_context_lines,
    offering_price,
    scenario_rows_matrix,
    year_projection_matrix,
)

st.set_page_config(page_title="CRE Scenarios", layout="wide", initial_sidebar_state="expanded")


def _pct(x: float) -> float:
    """Display percent (e.g. 6.25) to decimal rate."""
    return x / 100.0


def _caption_line(line: str) -> None:
    """Render a caption without Streamlit treating ``$`` as LaTeX math delimiters."""
    st.caption(line.replace("$", r"\$"))


def _sidebar_purchase_price_and_loan(
    *,
    price_raw: str,
    rate: float,
    amort: int,
    balloon: int,
    loan_down_pct: float,
) -> tuple[float, LoanTerms]:
    """Balloon block: loan sized from sidebar purchase price and shared loan down %."""
    price = parse_money_amount(price_raw)
    loan = LoanTerms(
        down_payment_fraction=_pct(loan_down_pct),
        annual_interest_rate=rate,
        amortization_years=amort,
        balloon_years=balloon,
    )
    return price, loan


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
            value=5,
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
            step=0.05,
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
    balloon_loan: LoanTerms | None,
    balloon_noi: float | None = None,
    balloon_list_price: float | None = None,
    balloon_offer_price: float | None = None,
    balloon_exit_noi: float | None = None,
    balloon_valuation_cap_rate: float | None = None,
    balloon_income_year: int | None = None,
    pdf_title: str,
    download_button_key: str,
    pdf_footer: list[str] | None = None,
) -> None:
    st.subheader("Scenario Results")
    for line in summary_lines:
        _caption_line(line)
    if balloon_loan is not None and (
        balloon_list_price is not None or balloon_offer_price is not None
    ):
        for line in balloon_context_lines(
            balloon_loan,
            net_operating_income=balloon_noi,
            list_price=balloon_list_price,
            offer_price=balloon_offer_price,
            exit_noi=balloon_exit_noi,
            valuation_cap_rate=balloon_valuation_cap_rate,
            income_year=balloon_income_year,
        ):
            _caption_line(line)

    headers, matrix = scenario_rows_matrix(rows)
    st.dataframe(pd.DataFrame(matrix, columns=headers), use_container_width=True, hide_index=True)

    extra_summary = list(summary_lines)
    if balloon_loan is not None and (
        balloon_list_price is not None or balloon_offer_price is not None
    ):
        extra_summary.extend(
            balloon_context_lines(
                balloon_loan,
                net_operating_income=balloon_noi,
                list_price=balloon_list_price,
                offer_price=balloon_offer_price,
                exit_noi=balloon_exit_noi,
                valuation_cap_rate=balloon_valuation_cap_rate,
                income_year=balloon_income_year,
            )
        )

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


def _render_year_projection(
    *,
    stated_noi: StatedNoi,
    loan: LoanTerms,
    offer_price: float,
    y1_noi: float,
    horizon_years: int,
) -> None:
    """Year-by-year NOI, cash flow, DSCR, and LTV at the fixed offer price."""
    if offer_price <= 0 or y1_noi <= 0:
        return
    valuation_cap = y1_noi / offer_price
    projection = build_year_projection(
        going_in_price=offer_price,
        stated_noi=stated_noi,
        loan=loan,
        valuation_cap_rate=valuation_cap,
        years=int(horizon_years),
    )
    st.subheader("Year-by-Year Projection")
    st.caption(
        f"Acquisition anchored at offer ${offer_price:,.0f} with going-in cap "
        f"{valuation_cap:.2%} (Y1 NOI ÷ price). Debt service is fixed; NOI, cash flow, "
        f"DSCR, and LTV move with escalation."
    )
    headers, matrix = year_projection_matrix(projection)
    st.dataframe(pd.DataFrame(matrix, columns=headers), use_container_width=True, hide_index=True)
    chart_df = pd.DataFrame(
        {
            "NOI": [r.net_operating_income for r in projection],
            "Cash Flow": [r.cash_flow for r in projection],
        },
        index=[r.year for r in projection],
    )
    st.line_chart(chart_df, use_container_width=True)


def tab_cap_fixed(
    rate: float,
    amort: int,
    balloon: int,
    sweep: CapRateSweep,
    *,
    price_raw: str,
    operating_noi_raw: str,
    loan_down_pct: float,
) -> None:
    st.subheader("Cap Rate Sweep at a Fixed Purchase Price")
    st.caption(
        "NOI = purchase price × each row’s assumed going-in cap. "
        "Purchase price and loan down % are in the sidebar (shared); center cap anchors the grid."
    )

    try:
        price = parse_money_amount(price_raw)
        listing = Listing(
            purchase_price=price,
            listing_cap_rate=sweep.center_cap_rate,
        )
        loan = LoanTerms(
            down_payment_fraction=_pct(loan_down_pct),
            annual_interest_rate=rate,
            amortization_years=amort,
            balloon_years=balloon,
        )
        rows = build_cap_rate_scenarios(listing, loan, sweep)
        balloon_noi = parse_money_amount(operating_noi_raw)
        balloon_offer_price = parse_money_amount(price_raw)
        balloon_list_price = offering_price(balloon_noi, sweep.center_cap_rate)
        rows = inject_offer_cap_row(
            rows,
            operating_income=balloon_noi,
            offer_price=balloon_offer_price,
            list_price=balloon_list_price,
            loan=loan,
            implied_price_mode=False,
        )
        _, balloon_loan = _sidebar_purchase_price_and_loan(
            price_raw=price_raw,
            rate=rate,
            amort=amort,
            balloon=balloon,
            loan_down_pct=loan_down_pct,
        )
        summary = [
            f"Purchase ${listing.purchase_price:,.0f}; center cap {sweep.center_cap_rate:.2%}; "
            f"loan {rate:.4%} {amort}yr/{balloon}yr balloon; down {loan_down_pct:.2f}%."
        ]
        _render_table_and_pdf(
            rows,
            summary,
            balloon_loan=balloon_loan,
            balloon_noi=balloon_noi,
            balloon_list_price=balloon_list_price,
            balloon_offer_price=balloon_offer_price,
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
    price_raw: str,
    operating_noi_raw: str,
) -> None:
    st.subheader("Cap Sweep to Implied Purchase Price")
    st.caption(
        "Going-in price = Year-1 NOI ÷ cap, sized at acquisition for every cap row. "
        "Set NOI growth below to drive the year-by-year projection and balloon exit. "
        "Loan down % is in the sidebar."
    )

    with st.container():
        esc_model = st.radio(
            "NOI Growth",
            ["Annual (Compound Each Year)", "Step on a Schedule"],
            horizontal=True,
            key=IMPLIED_ESC_MODEL_KEY,
        )
        annual_esc = esc_model.startswith("Annual")
        esc_pct = st.number_input(
            "Annual Escalator (%/yr, 0 if None)",
            value=0.0,
            step=0.1,
            format="%.4f",
            key=IMPLIED_ESC_PCT_KEY,
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
                key=IMPLIED_STEP_EVERY_KEY,
                disabled=annual_esc,
            )
        with c_step[1]:
            step_unit = st.selectbox(
                "Period Unit",
                ["yrs", "mo"],
                index=0,
                key=IMPLIED_STEP_UNIT_KEY,
                disabled=annual_esc,
            )
        with c_step[2]:
            step_kind = st.selectbox(
                "Increase Type",
                ["%", "$"],
                index=0,
                key=IMPLIED_STEP_KIND_KEY,
                disabled=annual_esc,
            )
        with c_step[3]:
            step_amt_pct = st.number_input(
                "Increase (%/Step)",
                value=3.0,
                step=0.1,
                format="%.4f",
                key=IMPLIED_STEP_AMT_PCT_KEY,
                disabled=annual_esc or step_kind != "%",
                help="Display percent per completed period (e.g. 3 = 3%).",
            )
            step_amt_money = st.text_input(
                "Increase ($/Step)",
                value="1000",
                key=IMPLIED_STEP_AMT_MONEY_KEY,
                disabled=annual_esc or step_kind != "$",
                help="Dollar bump per completed period (e.g. 1k, 2500).",
            )
        projection_horizon = st.number_input(
            "Projection Horizon (Yr)",
            min_value=1,
            max_value=30,
            value=10,
            key=IMPLIED_PROJECTION_HORIZON_KEY,
            help="Years shown in the year-by-year projection table and chart.",
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
        y1_noi = stated_noi.operating_income_year(1)
    except ValueError as e:
        st.error(str(e))
        return

    try:
        rates = LoanRateTerms(rate, amort, balloon)
        rows = build_cap_implied_price_scenarios(
            operating_income=y1_noi,
            down_payment_fraction=_pct(loan_down_pct),
            loan_rates=rates,
            cap_sweep=sweep,
        )
        loan = rates.with_down_payment(_pct(loan_down_pct))
        cc = sweep.center_cap_rate
        ref_p = y1_noi / cc if cc else 0.0
        offer_price = parse_money_amount(price_raw)
        valuation_cap = y1_noi / offer_price if offer_price > 0 else 0.0
        rows = inject_offer_cap_row(
            rows,
            operating_income=y1_noi,
            offer_price=offer_price,
            list_price=ref_p,
            loan=loan,
            implied_price_mode=True,
            down_payment_fraction=_pct(loan_down_pct),
        )
        _, balloon_loan = _sidebar_purchase_price_and_loan(
            price_raw=price_raw,
            rate=rate,
            amort=amort,
            balloon=balloon,
            loan_down_pct=loan_down_pct,
        )
        exit_noi = stated_noi.operating_income_year(balloon)
        summary = [
            f"Going-in NOI ${y1_noi:,.0f} — same for every cap row "
            f"(shown here only; omitted from the table).",
            f"Down {loan_down_pct:.2f}%; loan {rate:.4%} {amort}yr/{balloon}yr balloon; "
            f"going-in reference price @ center cap ≈ ${ref_p:,.0f}.",
        ]
        _render_table_and_pdf(
            rows,
            summary,
            balloon_loan=balloon_loan,
            balloon_noi=y1_noi,
            balloon_list_price=ref_p,
            balloon_offer_price=offer_price,
            balloon_exit_noi=exit_noi,
            balloon_valuation_cap_rate=valuation_cap,
            pdf_title="CRE Analysis — Implied Price (Cap on NOI)",
            download_button_key="pdf_dl_implied",
        )
        _render_year_projection(
            stated_noi=stated_noi,
            loan=loan,
            offer_price=offer_price,
            y1_noi=y1_noi,
            horizon_years=int(projection_horizon),
        )
    except ValueError as e:
        st.error(str(e))


def tab_down_sweep(
    rate: float,
    amort: int,
    balloon: int,
    cap_sweep: CapRateSweep,
    *,
    price_raw: str,
    operating_noi_raw: str,
    loan_down_pct: float,
) -> None:
    st.subheader("Down Payment Sweep")
    st.caption(
        "Fixed price and NOI; LTV and cash-on-cash move with equity. "
        "Purchase price and operating NOI are in the sidebar; center cap labels rows and balloon list price."
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
            listing_cap_for_display=cap_sweep.center_cap_rate,
            loan_rates=rates,
            sweep=sweep,
        )
        _, balloon_loan = _sidebar_purchase_price_and_loan(
            price_raw=price_raw,
            rate=rate,
            amort=amort,
            balloon=balloon,
            loan_down_pct=loan_down_pct,
        )
        ref_cap = cap_sweep.center_cap_rate
        summary = [
            f"Price ${price:,.0f}; NOI ${noi:,.0f}/yr; ref. cap {ref_cap:.2%}; "
            f"loan {rate:.4%} {amort}yr/{balloon}yr."
        ]
        _render_table_and_pdf(
            rows,
            summary,
            balloon_loan=balloon_loan,
            balloon_noi=noi,
            balloon_list_price=offering_price(noi, ref_cap),
            balloon_offer_price=price,
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
        st.header("Deal: Price, Income, Loan Down")
        st.caption(
            "**Implied Price:** Y1 / operating NOI and loan down % (price = NOI ÷ row cap). "
            "**Down Payment:** same price and NOI; that tab’s down % grid replaces sidebar loan down "
            "for sizing. **Cap at Fixed Price:** purchase price and loan down % (NOI = price × row cap)."
        )
        lp, rp = _sidebar_label_field()
        with lp:
            st.caption("Purchase Price")
        with rp:
            price_raw = st.text_input(
                "purchase_price",
                value="2.597M",
                label_visibility="collapsed",
                help="e.g. 2.597M, 874k — scenario tabs plus balloon/cash-flow lines on every tab.",
                key=SHARED_PURCHASE_PRICE_KEY,
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
                value="155.808k",
                label_visibility="collapsed",
                key=SHARED_OPERATING_NOI_RAW_KEY,
                help="Implied tab (stated Y1) and down sweep (annual NOI).",
            )
        st.divider()
        st.subheader("Going-In Cap Grid")
        st.caption(
            "Center cap, step size, and how many rows below/above center. "
            "Each scenario row is one going-in cap—on **Implied Price** (price = NOI ÷ cap) "
            "and **Cap at Fixed Price** (NOI = price × cap). "
            "Center cap also labels **Down Payment** rows and balloon list price."
        )
        sweep = _sweep_cap_inputs(
            label_prefix="",
            key_prefix=SHARED_CAP_SWEEP_WIDGET_KEY_PREFIX,
        )
        st.divider()
        st.header("Mortgage Terms (All Tabs)")
        st.caption(
            "Interest rate, amortization, and balloon maturity—used everywhere "
            "the model sizes annual debt service and LTV."
        )
        rate, amort, balloon = _loan_inputs(
            label_prefix="",
            key_prefix=SHARED_LOAN_WIDGET_KEY_PREFIX,
        )

    tab1, tab2, tab3 = st.tabs(["Implied Price", "Down Payment", "Cap at Fixed Price"])
    with tab1:
        tab_implied_price(
            rate,
            amort,
            balloon,
            sweep,
            loan_down_pct=loan_down_pct,
            price_raw=price_raw,
            operating_noi_raw=operating_noi_raw,
        )
    with tab2:
        tab_down_sweep(
            rate,
            amort,
            balloon,
            sweep,
            price_raw=price_raw,
            operating_noi_raw=operating_noi_raw,
            loan_down_pct=loan_down_pct,
        )
    with tab3:
        tab_cap_fixed(
            rate,
            amort,
            balloon,
            sweep,
            price_raw=price_raw,
            operating_noi_raw=operating_noi_raw,
            loan_down_pct=loan_down_pct,
        )


if __name__ == "__main__":
    main()
