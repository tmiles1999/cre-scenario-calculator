"""Professional PDF export for scenario tables (ReportLab)."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape


def build_scenario_pdf(
    *,
    title: str = "CRE Underwriting Scenarios",
    subtitle: str | None = None,
    summary_lines: list[str],
    headers: list[str],
    rows: list[list[str]],
    footer_lines: list[str] | None = None,
) -> bytes:
    """Return PDF bytes: title, summary, styled table, optional footer."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=title,
    )
    styles = getSampleStyleSheet()
    meta = ParagraphStyle(
        name="Meta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#555555"),
        spaceAfter=6,
    )
    body = ParagraphStyle(
        name="Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=4,
    )

    story: list = []
    story.append(Paragraph(escape(title), styles["Title"]))
    story.append(
        Paragraph(
            escape(subtitle or datetime.now().strftime("%B %d, %Y")),
            meta,
        )
    )
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("<b>Assumptions &amp; Context</b>", styles["Heading2"]))
    for line in summary_lines:
        story.append(Paragraph(escape(line), body))
    story.append(Spacer(1, 0.2 * inch))

    table_data: list[list[str]] = [headers] + rows
    tbl = Table(table_data, repeatRows=1, hAlign="RIGHT")
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cfd8dc")),
                ("TOPPADDING", (0, 1), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(tbl)

    if footer_lines:
        story.append(Spacer(1, 0.25 * inch))
        story.append(Paragraph("<b>Notes</b>", styles["Heading2"]))
        for line in footer_lines:
            story.append(Paragraph(escape(line), body))

    doc.build(story)
    return buf.getvalue()
