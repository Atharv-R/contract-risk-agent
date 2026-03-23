"""
PDF Report Exporter — Generates a professional, downloadable risk report.

Uses fpdf2 to create a clean PDF with:
  - Cover section with overall risk score
  - Executive summary
  - Clause-by-clause analysis table
  - Detailed findings for high-risk clauses
  - Missing clauses and negotiation points
"""

from fpdf import FPDF
from pathlib import Path
from datetime import datetime


# ── Color Scheme ─────────────────────────────────────────────────

COLORS = {
    "critical": (220, 38, 38),     # Red
    "high":     (234, 88, 12),     # Orange
    "medium":   (202, 138, 4),     # Yellow/Amber
    "low":      (22, 163, 74),     # Green
    "header":   (30, 58, 138),     # Dark blue
    "light_bg": (241, 245, 249),   # Light gray-blue
    "white":    (255, 255, 255),
    "black":    (30, 30, 30),
    "gray":     (100, 100, 100),
}

def _clean(text) -> str:
    """
    Replace Unicode characters that built-in PDF fonts can't handle.
    LLM responses often contain fancy quotes, dashes, etc.
    """
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "\u2014": "-",   # em-dash —
        "\u2013": "-",   # en-dash –
        "\u2018": "'",   # left single quote '
        "\u2019": "'",   # right single quote '
        "\u201c": '"',   # left double quote "
        "\u201d": '"',   # right double quote "
        "\u2026": "...", # ellipsis …
        "\u2022": "-",   # bullet •
        "\u00a0": " ",   # non-breaking space
        "\u200b": "",    # zero-width space
        "\u2032": "'",   # prime ′
        "\u2033": '"',   # double prime ″
        "\uf0b7": "-",   # bullet variant
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Catch anything else outside latin-1
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text

def _risk_color(level: str) -> tuple:
    return COLORS.get(level.lower(), COLORS["gray"])


class RiskReportPDF(FPDF):
    """Custom PDF class with header/footer."""

    def __init__(self, contract_name: str = ""):
        super().__init__()
        self.contract_name = contract_name

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*COLORS["gray"])
        self.cell(0, 10, _clean(f"Risk Report - {self.contract_name}"), align="L",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*COLORS["gray"])
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        self.ln(6)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*COLORS["header"])
        self.cell(0, 10, _clean(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*COLORS["header"])
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*COLORS["black"])
        self.multi_cell(0, 5.5, _clean(text))
        self.ln(2)

    def risk_badge(self, level: str, score: float):
        color = _risk_color(level)
        self.set_fill_color(*color)
        self.set_text_color(*COLORS["white"])
        self.set_font("Helvetica", "B", 10)
        label = f" {level.upper()} ({score}) "
        self.cell(45, 7, _clean(label), fill=True, align="C")
        self.set_text_color(*COLORS["black"])


def generate_pdf_report(report: dict, output_path: str = None) -> bytes:
    """
    Generate a PDF risk report from the analysis results.
    """
    contract_name = report.get("contract_name", "Unknown Contract")
    pdf = RiskReportPDF(contract_name=contract_name)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Page 1: Cover ────────────────────────────────────────────
    pdf.add_page()

    # Blue header bar
    pdf.set_fill_color(*COLORS["header"])
    pdf.rect(0, 0, 210, 45, "F")

    pdf.set_y(12)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*COLORS["white"])
    pdf.cell(0, 10, "CONTRACT RISK ANALYSIS", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Automated Risk Assessment Report", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(15)
    pdf.set_text_color(*COLORS["black"])

    # Contract info
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(40, 7, "Contract:", new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _clean(contract_name), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(40, 7, "Analyzed:", new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", "B", 11)
    analyzed_at = report.get("analyzed_at", "")
    try:
        dt = datetime.fromisoformat(analyzed_at)
        date_str = dt.strftime("%B %d, %Y at %I:%M %p UTC")
    except (ValueError, TypeError):
        date_str = str(analyzed_at)
    pdf.cell(0, 7, _clean(date_str), new_x="LMARGIN", new_y="NEXT")

    parties = report.get("parties", [])
    if parties:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(40, 7, "Parties:", new_x="RIGHT", new_y="TOP")
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _clean(", ".join(parties[:4])), new_x="LMARGIN", new_y="NEXT")

    # Overall risk score
    pdf.ln(10)
    overall_level = report.get("overall_risk_level", "medium")
    overall_score = report.get("overall_risk_score", 0.5)
    risk_color_val = _risk_color(overall_level)

    pdf.set_fill_color(*risk_color_val)
    pdf.set_text_color(*COLORS["white"])
    pdf.set_font("Helvetica", "B", 16)
    y_pos = pdf.get_y()
    pdf.set_xy(55, y_pos)
    pdf.cell(100, 14, _clean(f"OVERALL RISK: {overall_level.upper()} ({overall_score})"),
             fill=True, align="C")
    pdf.set_text_color(*COLORS["black"])
    pdf.ln(20)

    # Quick stats
    pdf.set_font("Helvetica", "", 11)
    clause_count = report.get("clause_count", 0)
    high_count = report.get("high_risk_count", 0)
    missing_count = len(report.get("missing_clauses", []))
    recommendation = report.get("overall_recommendation", "review").upper()

    stats_line = f"Clauses: {clause_count}  |  High/Critical: {high_count}  |  Missing: {missing_count}"
    pdf.cell(0, 7, _clean(stats_line), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, _clean(f"Recommendation: {recommendation}"), align="C",
             new_x="LMARGIN", new_y="NEXT")

    # ── Executive Summary ────────────────────────────────────────
    pdf.section_title("EXECUTIVE SUMMARY")
    exec_summary = report.get("executive_summary", "No executive summary available.")
    pdf.body_text(exec_summary)

    # ── Top Issues ───────────────────────────────────────────────
    top_issues = report.get("top_issues", [])
    if top_issues:
        pdf.section_title("TOP ISSUES")
        for i, issue in enumerate(top_issues[:5], 1):
            severity = issue.get("severity", "medium")
            color = _risk_color(severity)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*color)
            pdf.cell(0, 6, _clean(f"{i}. [{severity.upper()}] {issue.get('issue', '')}"),
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*COLORS["black"])
            pdf.set_font("Helvetica", "", 10)
            action = issue.get("action", "")
            if action:
                pdf.cell(8, 6, "")
                pdf.cell(0, 6, _clean(f"Action: {action}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

    # ── Clause Analysis Table ────────────────────────────────────
    pdf.add_page()
    pdf.section_title("CLAUSE-BY-CLAUSE ANALYSIS")

    # Table header
    pdf.set_fill_color(*COLORS["header"])
    pdf.set_text_color(*COLORS["white"])
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(28, 8, "Section", fill=True, border=1)
    pdf.cell(28, 8, "Type", fill=True, border=1)
    pdf.cell(18, 8, "Risk", fill=True, border=1)
    pdf.cell(14, 8, "Score", fill=True, border=1)
    pdf.cell(102, 8, "Summary", fill=True, border=1)
    pdf.ln()

    # Table rows
    pdf.set_text_color(*COLORS["black"])
    for i, a in enumerate(report.get("clause_analyses", [])):
        level = a.get("risk_level", "medium")
        color = _risk_color(level)

        if i % 2 == 0:
            pdf.set_fill_color(*COLORS["light_bg"])
        else:
            pdf.set_fill_color(*COLORS["white"])

        pdf.set_font("Helvetica", "", 8)
        section = _clean(str(a.get("section_title", a.get("section_id", "?"))))[:18]
        ctype = _clean(str(a.get("clause_type", "?")))[:18]
        summary = _clean(str(a.get("summary", "")))[:65]
        score = str(a.get("risk_score", "?"))

        pdf.cell(28, 7, section, fill=True, border=1)
        pdf.cell(28, 7, ctype, fill=True, border=1)

        pdf.set_fill_color(*color)
        pdf.set_text_color(*COLORS["white"])
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(18, 7, level.upper(), fill=True, border=1, align="C")

        pdf.set_text_color(*COLORS["black"])
        pdf.set_fill_color(*(COLORS["light_bg"] if i % 2 == 0 else COLORS["white"]))
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(14, 7, score, fill=True, border=1, align="C")
        pdf.cell(102, 7, summary, fill=True, border=1)
        pdf.ln()

    # ── Detailed Findings ────────────────────────────────────────
    high_risk = [
        a for a in report.get("clause_analyses", [])
        if a.get("risk_level") in ("high", "critical")
    ]

    if high_risk:
        pdf.add_page()
        pdf.section_title("DETAILED FINDINGS - HIGH & CRITICAL RISK")

        for a in high_risk:
            level = a.get("risk_level", "medium")
            color = _risk_color(level)
            title = a.get("section_title", a.get("section_id", "Unknown"))

            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*color)
            header = f"{a.get('section_id', '?')}. {title} - {level.upper()} ({a.get('risk_score', '?')})"
            pdf.cell(0, 8, _clean(header), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*COLORS["black"])

            if a.get("summary"):
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 6, "Summary:", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, _clean(a["summary"]))

            if a.get("plain_english"):
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 6, "What this means:", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, _clean(a["plain_english"]))

            risks = a.get("risks_found", [])
            if risks:
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 6, "Risks:", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 9)
                for r in risks[:5]:
                    pdf.cell(6, 5, "")
                    pdf.cell(0, 5, _clean(f"- {r}"), new_x="LMARGIN", new_y="NEXT")

            if a.get("recommendation"):
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 6, "Recommendation:", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, _clean(a["recommendation"]))

            pdf.ln(6)

    # ── Missing Clauses ──────────────────────────────────────────
    missing = report.get("missing_clauses", [])
    if missing:
        pdf.section_title("MISSING CLAUSES")
        for m in missing:
            pdf.set_font("Helvetica", "B", 10)
            importance = m.get("importance", "medium")
            color = _risk_color("high" if importance == "high" else "medium")
            pdf.set_text_color(*color)
            clause_name = m.get("clause_type", "?").replace("_", " ").title()
            pdf.cell(0, 7, _clean(f"Missing: {clause_name} ({importance.upper()})"),
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*COLORS["black"])
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, _clean(m.get("plain_english", "")))
            pdf.ln(3)

    # ── Negotiation Points ───────────────────────────────────────
    points = report.get("negotiation_points", [])
    if points:
        pdf.section_title("NEGOTIATION POINTS")
        pdf.set_font("Helvetica", "", 10)
        for i, point in enumerate(points[:8], 1):
            pdf.cell(0, 6, _clean(f"{i}. {point}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

    # ── Disclaimer ───────────────────────────────────────────────
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*COLORS["gray"])
    pdf.multi_cell(0, 4, _clean(
        "DISCLAIMER: This report was generated by an AI-powered analysis tool and is intended "
        "for informational purposes only. It does not constitute legal advice. Please consult "
        "a qualified attorney before making decisions based on this analysis."
    ))

    # ── Output ───────────────────────────────────────────────────
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        pdf.output(output_path)

    return pdf.output()


# ── Direct Testing ───────────────────────────────────────────────

if __name__ == "__main__":
    import json
    from rich import print as rprint

    report_path = Path("data/outputs/risk_report.json")
    if not report_path.exists():
        rprint("[red]No report found. Run the agent first: python -m src.agent.graph[/red]")
        exit(1)

    with open(report_path) as f:
        report = json.load(f)

    output = "data/outputs/risk_report.pdf"
    generate_pdf_report(report, output_path=output)
    rprint(f"[green]✓ PDF report saved to: {output}[/green]")