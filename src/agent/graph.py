"""
Agent Graph — Assembles the LangGraph pipeline and provides
the main entry point for analyzing contracts.

Usage:
    from src.agent.graph import analyze_contract
    report = analyze_contract("path/to/contract.pdf")
"""

from langgraph.graph import StateGraph, START, END

from src.agent.state import AgentState
from src.agent.nodes import (
    parse_document,
    extract_entities_node,
    analyze_clauses,
    check_missing,
    generate_report,
)


# ── Build the Graph ──────────────────────────────────────────────

def build_graph():
    """
    Construct the LangGraph state machine.

    Flow:
      START → parse → entities → analyze → missing → report → END
    """
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("parse_document", parse_document)
    builder.add_node("extract_entities", extract_entities_node)
    builder.add_node("analyze_clauses", analyze_clauses)
    builder.add_node("check_missing", check_missing)
    builder.add_node("generate_report", generate_report)

    # Define the flow
    builder.add_edge(START, "parse_document")
    builder.add_edge("parse_document", "extract_entities")
    builder.add_edge("extract_entities", "analyze_clauses")
    builder.add_edge("analyze_clauses", "check_missing")
    builder.add_edge("check_missing", "generate_report")
    builder.add_edge("generate_report", END)

    return builder.compile()


# ── Singleton graph instance ─────────────────────────────────────

_graph = None


def get_graph():
    """Get or create the compiled graph (reusable)."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ── Main Entry Point ─────────────────────────────────────────────

def analyze_contract(pdf_path: str) -> dict:
    """
    Analyze a contract PDF and return a complete risk report.

    This is the ONE function the rest of the app calls.
    It runs the full pipeline: parse → NER → RAG + LLM → report.

    Args:
        pdf_path: Path to the PDF contract file.

    Returns:
        Complete risk report dict with:
          - overall_risk_score
          - overall_risk_level
          - executive_summary
          - clause_analyses (per-clause breakdown)
          - missing_clauses
          - negotiation_points
          - and more
    """
    graph = get_graph()

    # Initial state — only pdf_path is required, everything else
    # gets populated by the nodes as they run
    initial_state = {
        "pdf_path": pdf_path,
        "raw_text": "",
        "chunks": [],
        "metadata": {},
        "entities": {},
        "clause_analyses": [],
        "missing_clauses": [],
        "risk_report": {},
        "status": "starting",
        "errors": [],
    }

    # Run the graph
    final_state = graph.invoke(initial_state)

    return final_state["risk_report"]


# ── Direct Testing ───────────────────────────────────────────────

if __name__ == "__main__":
    import json
    from pathlib import Path
    from rich import print as rprint
    from rich.panel import Panel
    from rich.table import Table

    SAMPLE_PDF = "data/sample_contracts/sample_msa_risky.pdf"

    if not Path(SAMPLE_PDF).exists():
        rprint("[red]Sample contract not found. Run: python scripts/create_sample_contract.py[/red]")
        exit(1)

    rprint(Panel("[bold]Contract Risk Agent — Full Pipeline Test[/bold]", style="blue"))

    report = analyze_contract(SAMPLE_PDF)

    # ── Display Results ──
    rprint(Panel(
        f"[bold]Overall Risk: {report['overall_risk_level'].upper()} "
        f"({report['overall_risk_score']})[/bold]",
        style="red" if report['overall_risk_score'] >= 0.6 else "yellow"
    ))

    # Executive Summary
    rprint(f"\n[bold]Executive Summary:[/bold]")
    rprint(report.get("executive_summary", "No summary generated."))

    # Clause Table
    table = Table(title="\nClause-by-Clause Analysis")
    table.add_column("Section", style="cyan", width=20)
    table.add_column("Type", style="blue", width=18)
    table.add_column("Risk", width=10)
    table.add_column("Score", width=8)
    table.add_column("Summary", width=45)

    for a in report.get("clause_analyses", []):
        level = a.get("risk_level", "?")
        style = {
            "critical": "bold red",
            "high": "red",
            "medium": "yellow",
            "low": "green",
        }.get(level, "white")

        table.add_row(
            a.get("section_title", a.get("section_id", "?"))[:20],
            a.get("clause_type", "?"),
            f"[{style}]{level.upper()}[/{style}]",
            str(a.get("risk_score", "?")),
            a.get("summary", "")[:45],
        )

    rprint(table)

    # Missing Clauses
    if report.get("missing_clauses"):
        rprint(f"\n[bold yellow]Missing Clauses:[/bold yellow]")
        for m in report["missing_clauses"]:
            rprint(f"  ⚠ {m.get('clause_type', '?')} — {m.get('plain_english', '')[:80]}")

    # Negotiation Points
    if report.get("negotiation_points"):
        rprint(f"\n[bold]Negotiation Points:[/bold]")
        for point in report["negotiation_points"]:
            rprint(f"  → {point}")

    # Save full report
    output_path = Path("data/outputs/risk_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    rprint(f"\n[green]Full report saved to: {output_path}[/green]")