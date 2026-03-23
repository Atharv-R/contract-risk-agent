"""
Agent State — Defines the data that flows through the LangGraph pipeline.

This is a TypedDict that LangGraph uses to track everything:
what's been parsed, what's been analyzed, what the final report looks like.
Each node reads from this state and writes updates back to it.
"""

from typing import TypedDict


class AgentState(TypedDict):
    """
    Complete state of the contract analysis agent.

    Each field gets populated by a different node in the graph:
      parse_document   → pdf_path, raw_text, chunks, metadata
      extract_entities → entities
      analyze_clauses  → clause_analyses
      check_missing    → missing_clauses
      generate_report  → risk_report
    """

    # ── Input ──
    pdf_path: str                   # Path to the uploaded PDF

    # ── Document Parsing ──
    raw_text: str                   # Full extracted text
    chunks: list                    # List of clause chunk dicts
    metadata: dict                  # PDF metadata (pages, extraction method, etc.)

    # ── Entity Extraction ──
    entities: dict                  # NER results (parties, dates, money, etc.)

    # ── Clause Analysis ──
    clause_analyses: list           # Per-clause risk analysis from LLM

    # ── Gap Analysis ──
    missing_clauses: list           # Important clauses not found

    # ── Final Report ──
    risk_report: dict               # Complete compiled risk report

    # ── Pipeline Status ──
    status: str                     # Current step: "parsing", "analyzing", etc.
    errors: list                    # Any errors encountered (non-fatal)