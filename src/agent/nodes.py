"""
Graph Nodes — Each function is one step in the analysis pipeline.

Each node:
  1. Reads what it needs from the state
  2. Does its work (parsing, NER, LLM calls, etc.)
  3. Returns a dict of state updates
"""

import time
from datetime import datetime, timezone

from src.parser.pdf_extractor import extract_pdf
from src.parser.clause_chunker import chunk_contract
from src.ner.legal_ner import extract_entities, extract_entities_from_chunks, get_contract_summary
from src.rag.retriever import retrieve_for_risk_analysis
from src.rag.store import get_chroma_client, get_or_create_collection, ingest_clause_library
from src.agent.llm import call_gemini, parse_json_response
from src.agent.prompts import (
    CLAUSE_ANALYSIS_SYSTEM,
    CLAUSE_ANALYSIS_PROMPT,
    MISSING_CLAUSES_SYSTEM,
    MISSING_CLAUSES_PROMPT,
    EXECUTIVE_SUMMARY_SYSTEM,
    EXECUTIVE_SUMMARY_PROMPT,
)
from src.agent.state import AgentState


# ── Helper: Make sure vector store is ready ──────────────────────

def _ensure_vectorstore():
    """Auto-ingest clause library if vector store is empty."""
    client = get_chroma_client()
    collection = get_or_create_collection(client)
    if collection.count() == 0:
        print("  📚 Vector store empty — ingesting clause library...")
        ingest_clause_library()


# ── Node 1: Parse Document ───────────────────────────────────────

def parse_document(state: AgentState) -> dict:
    """
    PDF → raw text → clause-level chunks.

    Takes the pdf_path from state, extracts text, and splits
    into clause-level chunks ready for analysis.
    """
    print("\n📄 Step 1/5: Parsing document...")

    pdf_path = state["pdf_path"]
    doc = extract_pdf(pdf_path)

    # Chunk into clauses
    chunks = chunk_contract(doc.full_text)

    # Convert to plain dicts for state storage
    chunks_data = []
    for chunk in chunks:
        chunks_data.append({
            "text": chunk.text,
            "section_id": chunk.section_id,
            "section_title": chunk.section_title,
            "chunk_index": chunk.chunk_index,
            "char_count": chunk.char_count,
        })

    print(f"   ✓ Extracted {doc.total_pages} pages, {len(chunks_data)} clause chunks")

    return {
        "raw_text": doc.full_text,
        "chunks": chunks_data,
        "metadata": {
            "filename": doc.filename,
            "total_pages": doc.total_pages,
            "total_characters": doc.metadata.get("total_characters", 0),
            "extraction_method": doc.metadata.get("extraction_method", ""),
        },
        "status": "parsed",
        "errors": [],
    }


# ── Node 2: Extract Entities ────────────────────────────────────

def extract_entities_node(state: AgentState) -> dict:
    """
    Run NER on every chunk to find parties, dates, money, jurisdictions, etc.
    """
    print("🔍 Step 2/5: Extracting entities...")

    # We need to recreate lightweight chunk objects for the NER function
    from src.parser.clause_chunker import ClauseChunk

    chunks = []
    for c in state["chunks"]:
        chunks.append(ClauseChunk(
            text=c["text"],
            section_id=c["section_id"],
            section_title=c["section_title"],
            chunk_index=c["chunk_index"],
        ))

    results = extract_entities_from_chunks(chunks)

    # Get the aggregated summary
    summary = get_contract_summary(results["aggregated"])

    # Serialize per-chunk entities for state
    by_chunk = {}
    for idx, contract_entities in results["by_chunk"].items():
        by_chunk[str(idx)] = {
            "parties": [e.text for e in contract_entities.parties],
            "dates": [e.text for e in contract_entities.dates],
            "durations": [e.text for e in contract_entities.durations],
            "money": [e.text for e in contract_entities.money],
            "jurisdictions": [e.text for e in contract_entities.jurisdictions],
            "legal_terms": [e.text for e in contract_entities.legal_terms],
        }

    print(f"   ✓ Found {summary['entity_counts']['total']} entities")
    print(f"   Parties: {summary['parties'][:3]}")

    return {
        "entities": {
            "by_chunk": by_chunk,
            "summary": summary,
        },
        "status": "entities_extracted",
    }


# ── Node 3: Analyze Clauses ─────────────────────────────────────

def analyze_clauses(state: AgentState) -> dict:
    """
    The core analysis step. For each clause:
      1. Retrieve relevant baseline from the clause library (RAG)
      2. Send clause + baseline to Gemini for risk analysis
      3. Parse the structured response
    """
    print("⚖️  Step 3/5: Analyzing clauses with AI...")

    _ensure_vectorstore()

    chunks = state["chunks"]
    entities_by_chunk = state["entities"]["by_chunk"]
    analyses = []
    errors = list(state.get("errors", []))

    for i, chunk in enumerate(chunks):
        chunk_idx = str(chunk["chunk_index"])
        section_label = chunk["section_title"] or chunk["section_id"] or f"Chunk {i+1}"
        print(f"   Analyzing [{i+1}/{len(chunks)}]: {section_label}...")

        try:
            # ── Step A: RAG retrieval ──
            rag_results = retrieve_for_risk_analysis(chunk["text"], top_k=3)

            # Format baseline context for the prompt
            baseline_parts = []
            for match in rag_results.get("general_matches", [])[:3]:
                baseline_parts.append(
                    f"[{match.clause_type} — {match.section}]\n{match.text}"
                )
            baseline_context = "\n\n---\n\n".join(baseline_parts) if baseline_parts else "No specific baseline found."

            # ── Step B: Format entities for this chunk ──
            chunk_entities = entities_by_chunk.get(chunk_idx, {})
            entities_text = ""
            for etype, values in chunk_entities.items():
                if values:
                    entities_text += f"  {etype}: {', '.join(values[:5])}\n"
            if not entities_text:
                entities_text = "  No specific entities detected."

            # ── Step C: Build and send prompt ──
            prompt = CLAUSE_ANALYSIS_PROMPT.format(
                section_id=chunk["section_id"],
                section_title=chunk["section_title"] or "Untitled",
                clause_text=chunk["text"][:3000],  # Truncate very long clauses
                baseline_context=baseline_context[:3000],
                entities_summary=entities_text,
            )

            response = call_gemini(prompt, system_prompt=CLAUSE_ANALYSIS_SYSTEM)
            analysis = parse_json_response(response)

            # ── Step D: Attach metadata ──
            analysis["section_id"] = chunk["section_id"]
            analysis["section_title"] = chunk["section_title"]
            analysis["chunk_index"] = chunk["chunk_index"]
            analysis["original_text"] = chunk["text"][:500]  # Keep a preview
            analysis["rag_clause_type"] = rag_results.get("best_clause_type", "unknown")

            # Validate risk_score is a number
            try:
                analysis["risk_score"] = float(analysis.get("risk_score", 0.5))
                analysis["risk_score"] = max(0.0, min(1.0, analysis["risk_score"]))
            except (ValueError, TypeError):
                analysis["risk_score"] = 0.5

            analyses.append(analysis)
            level = analysis.get("risk_level", "?")
            score = analysis.get("risk_score", 0)
            print(f"     → {level.upper()} (score: {score})")

        except Exception as e:
            print(f"     ⚠️  Error analyzing chunk: {e}")
            errors.append(f"Clause {chunk['section_id']}: {str(e)}")
            analyses.append({
                "section_id": chunk["section_id"],
                "section_title": chunk["section_title"],
                "chunk_index": chunk["chunk_index"],
                "risk_score": 0.5,
                "risk_level": "medium",
                "summary": "Analysis failed — manual review recommended",
                "error": str(e),
            })

        # Rate limiting: stay under 15 requests/minute
        if i < len(chunks) - 1:
            time.sleep(3)

    print(f"   ✓ Analyzed {len(analyses)} clauses")

    return {
        "clause_analyses": analyses,
        "status": "clauses_analyzed",
        "errors": errors,
    }


# ── Node 4: Check Missing Clauses ───────────────────────────────

def check_missing(state: AgentState) -> dict:
    """
    Identify important clause types that SHOULD be in the contract
    but weren't found.
    """
    print("🔎 Step 4/5: Checking for missing clauses...")

    # What clause types did we find?
    found_types = set()
    for analysis in state["clause_analyses"]:
        ct = analysis.get("clause_type", "")
        if ct and ct != "general":
            found_types.add(ct)
        # Also check RAG-detected type
        rct = analysis.get("rag_clause_type", "")
        if rct and rct != "unknown":
            found_types.add(rct)

    parties = state["entities"]["summary"].get("parties", [])

    # Build prompt
    prompt = MISSING_CLAUSES_PROMPT.format(
        found_types="\n".join(f"  • {ct}" for ct in sorted(found_types)) or "  (none identified)",
        parties=", ".join(parties[:4]) or "Unknown parties",
    )

    response = call_gemini(prompt, system_prompt=MISSING_CLAUSES_SYSTEM)
    parsed = parse_json_response(response)

    missing = parsed.get("missing_clauses", [])
    print(f"   ✓ Found {len(missing)} missing clause(s)")

    for m in missing:
        print(f"     → Missing: {m.get('clause_type', '?')} ({m.get('importance', '?')})")

    return {
        "missing_clauses": missing,
        "status": "missing_checked",
    }


# ── Node 5: Generate Report ─────────────────────────────────────

def generate_report(state: AgentState) -> dict:
    """
    Compile everything into the final risk report with an executive summary.
    """
    print("📊 Step 5/5: Generating risk report...")

    analyses = state["clause_analyses"]
    missing = state["missing_clauses"]
    entities_summary = state["entities"]["summary"]

    # ── Calculate overall risk score ──
    overall_score, overall_level = _calculate_overall_risk(analyses, missing)

    # ── Build clause summaries for the exec summary prompt ──
    clause_lines = []
    for a in analyses:
        clause_lines.append(
            f"- {a.get('section_id', '?')} {a.get('section_title', '?')}: "
            f"{a.get('risk_level', '?').upper()} ({a.get('risk_score', 0)}) — "
            f"{a.get('summary', 'No summary')}"
        )
    clause_summaries = "\n".join(clause_lines)

    missing_lines = []
    for m in missing:
        missing_lines.append(f"- {m.get('clause_type', '?')}: {m.get('plain_english', '')}")
    missing_summary = "\n".join(missing_lines) if missing_lines else "No critical missing clauses."

    # ── Get executive summary from LLM ──
    exec_summary = {}
    try:
        prompt = EXECUTIVE_SUMMARY_PROMPT.format(
            parties=", ".join(entities_summary.get("parties", [])[:4]),
            key_dates=", ".join(entities_summary.get("key_dates", [])[:4]),
            clause_count=len(analyses),
            clause_summaries=clause_summaries,
            missing_summary=missing_summary,
            overall_score=overall_score,
            overall_level=overall_level,
        )

        response = call_gemini(prompt, system_prompt=EXECUTIVE_SUMMARY_SYSTEM)
        exec_summary = parse_json_response(response)

        # If the LLM returned the summary nested or with a different key, dig for it
        if not exec_summary.get("executive_summary"):
            # Check if the entire response IS the summary (raw text instead of JSON)
            if exec_summary.get("error") and exec_summary.get("raw_response"):
                exec_summary["executive_summary"] = exec_summary["raw_response"]
            # Check for alternative key names the LLM might have used
            for alt_key in ["summary", "exec_summary", "overview", "analysis"]:
                if exec_summary.get(alt_key):
                    exec_summary["executive_summary"] = exec_summary[alt_key]
                    break

    except Exception as e:
        print(f"  ⚠️  Executive summary generation failed: {e}")

    # ── Fallback: build summary from data if LLM didn't produce one ──
    if not exec_summary.get("executive_summary"):
        high_risk = [a for a in analyses if a.get("risk_level") in ("high", "critical")]
        fallback_parts = [
            f"This contract has an overall risk level of {overall_level.upper()} "
            f"(score: {overall_score}/1.0).",
            f"Out of {len(analyses)} clauses analyzed, {len(high_risk)} were flagged as high or critical risk.",
        ]
        if high_risk:
            top_risks = ", ".join(
                a.get("section_title", a.get("section_id", "?"))
                for a in high_risk[:3]
            )
            fallback_parts.append(f"Key concerns include: {top_risks}.")
        if missing:
            fallback_parts.append(
                f"Additionally, {len(missing)} important clause type(s) appear to be missing."
            )
        fallback_parts.append("This contract should be carefully reviewed before signing.")
        exec_summary["executive_summary"] = " ".join(fallback_parts)
        print("  ℹ  Used fallback executive summary")

    # ── Fallback for other fields ──
    if not exec_summary.get("top_issues"):
        exec_summary["top_issues"] = [
            {
                "issue": a.get("summary", "Risk identified"),
                "severity": a.get("risk_level", "medium"),
                "action": a.get("recommendation", "Review this clause"),
            }
            for a in sorted(analyses, key=lambda x: x.get("risk_score", 0), reverse=True)[:3]
        ]

    if not exec_summary.get("overall_recommendation"):
        if overall_score >= 0.7:
            exec_summary["overall_recommendation"] = "reject"
        elif overall_score >= 0.4:
            exec_summary["overall_recommendation"] = "negotiate"
        else:
            exec_summary["overall_recommendation"] = "sign"

    if not exec_summary.get("negotiation_points"):
        exec_summary["negotiation_points"] = [
            a.get("recommendation", "Review this clause")
            for a in analyses
            if a.get("risk_level") in ("high", "critical") and a.get("recommendation")
        ][:5]

    # ── Compile final report ──
    risk_report = {
        "contract_name": state["metadata"].get("filename", "Unknown"),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "overall_risk_score": overall_score,
        "overall_risk_level": overall_level,
        "executive_summary": exec_summary.get("executive_summary", ""),
        "top_issues": exec_summary.get("top_issues", []),
        "overall_recommendation": exec_summary.get("overall_recommendation", "review"),
        "negotiation_points": exec_summary.get("negotiation_points", []),
        "parties": entities_summary.get("parties", []),
        "key_dates": entities_summary.get("key_dates", []),
        "clause_count": len(analyses),
        "high_risk_count": sum(
            1 for a in analyses
            if a.get("risk_level") in ("high", "critical")
        ),
        "clause_analyses": analyses,
        "missing_clauses": missing,
        "entity_summary": entities_summary,
        "metadata": state["metadata"],
    }

    print(f"\n{'═' * 50}")
    print(f"  ANALYSIS COMPLETE")
    print(f"  Overall Risk: {overall_level.upper()} ({overall_score})")
    print(f"  Clauses analyzed: {len(analyses)}")
    print(f"  High/Critical risks: {risk_report['high_risk_count']}")
    print(f"  Missing clauses: {len(missing)}")
    print(f"{'═' * 50}\n")

    return {
        "risk_report": risk_report,
        "status": "complete",
    }


# ── Scoring Logic ────────────────────────────────────────────────

def _calculate_overall_risk(
    analyses: list[dict],
    missing_clauses: list[dict],
) -> tuple[float, str]:
    """
    Calculate the overall contract risk score.

    Uses weighted average of clause scores, with higher-impact
    clause types weighted more heavily. Adds a penalty for
    missing important clauses.
    """
    if not analyses:
        return 0.5, "medium"

    # Clause types that carry more weight in overall risk
    type_weights = {
        "liability_cap": 1.5,
        "uncapped_liability": 1.5,
        "ip_assignment": 1.3,
        "non_compete": 1.2,
        "indemnification": 1.1,
        "auto_renewal": 1.0,
        "termination": 1.0,
        "governing_law": 0.9,
        "confidentiality": 0.8,
        "payment_terms": 0.8,
        "force_majeure": 0.7,
    }

    weighted_sum = 0.0
    total_weight = 0.0

    for analysis in analyses:
        clause_type = analysis.get("clause_type", "general")
        weight = type_weights.get(clause_type, 0.6)
        score = float(analysis.get("risk_score", 0.5))

        weighted_sum += score * weight
        total_weight += weight

    base_score = weighted_sum / total_weight if total_weight > 0 else 0.5

    # Penalty for missing important clauses
    high_missing = sum(1 for m in missing_clauses if m.get("importance") == "high")
    medium_missing = sum(1 for m in missing_clauses if m.get("importance") == "medium")
    missing_penalty = (high_missing * 0.04) + (medium_missing * 0.02)

    overall = min(1.0, round(base_score + missing_penalty, 2))

    # Determine level
    if overall >= 0.8:
        level = "critical"
    elif overall >= 0.6:
        level = "high"
    elif overall >= 0.35:
        level = "medium"
    else:
        level = "low"

    return overall, level