"""PDF export smoke test."""

import pytest


def test_build_scenario_pdf_non_trivial() -> None:
    pytest.importorskip("reportlab")
    from cre_calcs.pdf_report import build_scenario_pdf

    pdf = build_scenario_pdf(
        title="Test CRE report",
        summary_lines=["Line one of context.", "Line two."],
        headers=["A", "B"],
        rows=[["1", "2"], ["3", "4"]],
        footer_lines=["Disclaimer."],
    )
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 500
