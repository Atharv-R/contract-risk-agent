"""
Retriever — Queries the clause library to find relevant baselines.

Given a contract clause (e.g., about liability), this retrieves the most
relevant knowledge from our clause library (e.g., "what's standard for
liability caps", "red flags to watch for", etc.).

This is the R in RAG — the context that gets fed to the LLM.
"""

from dataclasses import dataclass, field

from src.rag.embedder import embed_text
from src.rag.store import get_chroma_client, get_or_create_collection


@dataclass
class RetrievalResult:
    """A single retrieved baseline chunk with its relevance score."""
    text: str                   # The baseline content
    clause_type: str            # "auto_renewal", "liability_cap", etc.
    section: str                # "Red Flags", "Standard and Acceptable"
    source_file: str            # Source markdown file
    similarity_score: float     # 0 to 1, higher = more relevant
    metadata: dict = field(default_factory=dict)


def retrieve_baseline(
    query_text: str,
    top_k: int = 5,
    clause_type_filter: str = None,
) -> list[RetrievalResult]:
    """
    Find the most relevant baseline knowledge for a given contract clause.

    Args:
        query_text:         The contract clause text to analyze.
        top_k:              Number of results to return.
        clause_type_filter: Optional — only search within a specific clause type
                            (e.g., "liability_cap"). If None, searches everything.

    Returns:
        List of RetrievalResult objects, sorted by relevance (best first).
    """
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    if collection.count() == 0:
        print("⚠️  Vector store is empty. Run: python -m src.rag.store")
        return []

    # Embed the query
    query_embedding = embed_text(query_text)

    # Build optional filter
    where_filter = None
    if clause_type_filter:
        where_filter = {"clause_type": clause_type_filter}

    # Query ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    # Parse results into our data structure
    retrieved = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            # ChromaDB returns L2 distances; convert to similarity score
            # Lower distance = more similar. We normalize to 0-1 range.
            distance = results["distances"][0][i]
            similarity = max(0, 1 - (distance / 2))  # Rough normalization

            meta = results["metadatas"][0][i]

            retrieved.append(RetrievalResult(
                text=doc,
                clause_type=meta.get("clause_type", ""),
                section=meta.get("section", ""),
                source_file=meta.get("source_file", ""),
                similarity_score=round(similarity, 4),
                metadata=meta,
            ))

    # Sort by similarity (best first)
    retrieved.sort(key=lambda r: r.similarity_score, reverse=True)

    return retrieved


def retrieve_for_risk_analysis(
    clause_text: str,
    top_k: int = 5,
) -> dict:
    """
    Retrieve baseline knowledge specifically structured for risk analysis.

    Returns both general matches and tries to get red flags + standards
    for the best-matching clause type.

    Args:
        clause_text: The contract clause to analyze.
        top_k: Number of general results.

    Returns:
        {
            "general_matches": [RetrievalResult, ...],
            "best_clause_type": "liability_cap",
            "red_flags": [RetrievalResult, ...],
            "standards": [RetrievalResult, ...],
        }
    """
    # Step 1: General retrieval to find the most relevant clause type
    general = retrieve_baseline(clause_text, top_k=top_k)

    if not general:
        return {
            "general_matches": [],
            "best_clause_type": "unknown",
            "red_flags": [],
            "standards": [],
        }

    # Step 2: Identify the best-matching clause type
    best_type = general[0].clause_type

    # Step 3: Get red flags and standards specifically for that clause type
    red_flags = retrieve_baseline(
        clause_text,
        top_k=2,
        clause_type_filter=best_type,
    )

    # Filter to get specifically the red flags and standards sections
    red_flag_results = [r for r in red_flags if "red flag" in r.section.lower()]
    standard_results = [r for r in red_flags if "standard" in r.section.lower() or "acceptable" in r.section.lower()]

    return {
        "general_matches": general,
        "best_clause_type": best_type,
        "red_flags": red_flag_results,
        "standards": standard_results,
    }


# ── Direct Testing ───────────────────────────────────────────────

if __name__ == "__main__":
    from rich import print as rprint
    from rich.panel import Panel
    from rich.table import Table

    test_clauses = [
        "This Agreement shall automatically renew for successive two year periods unless cancelled.",
        "Service Provider shall be liable for all damages without any cap or limitation.",
        "All intellectual property and inventions created shall be assigned to the Company.",
        "Service Provider shall not compete anywhere in North America for 36 months.",
        "Any disputes shall be resolved through binding arbitration selected by Company.",
    ]

    for clause in test_clauses:
        rprint(Panel(f"[bold]{clause[:80]}...[/bold]", title="Query Clause"))

        results = retrieve_for_risk_analysis(clause)
        rprint(f"  Best match type: [yellow]{results['best_clause_type']}[/yellow]")

        table = Table(show_header=True)
        table.add_column("Score", width=8)
        table.add_column("Type", width=20)
        table.add_column("Section", width=25)
        table.add_column("Preview", width=50)

        for r in results["general_matches"][:3]:
            preview = r.text[:80].replace("\n", " ")
            table.add_row(
                f"{r.similarity_score:.3f}",
                r.clause_type,
                r.section,
                preview + "..."
            )

        rprint(table)
        rprint("")