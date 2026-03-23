"""
Embedder — Wraps sentence-transformers to convert text into vectors.

Uses all-MiniLM-L6-v2: a small, fast model that produces 384-dimensional
embeddings. Runs entirely on your machine, no API calls needed.
"""

from sentence_transformers import SentenceTransformer

# ── Model Loading ────────────────────────────────────────────────

_model = None


def _get_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    """Lazy-load the embedding model (downloads ~80MB on first run)."""
    global _model
    if _model is None:
        print(f"  Loading embedding model: {model_name}...")
        _model = SentenceTransformer(model_name)
        print(f"  ✓ Model loaded ({_model.get_sentence_embedding_dimension()} dimensions)")
    return _model


# ── Public Functions ─────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    """
    Convert a single piece of text into a vector.

    Args:
        text: Any string (a clause, a query, etc.)

    Returns:
        List of floats (384 dimensions).
    """
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Convert multiple texts into vectors in one batch (faster than one-by-one).

    Args:
        texts: List of strings.

    Returns:
        List of embedding vectors.
    """
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    return embeddings.tolist()


# ── Direct Testing ───────────────────────────────────────────────

if __name__ == "__main__":
    from rich import print as rprint

    test_texts = [
        "This agreement shall automatically renew for successive one year periods.",
        "The liability of the service provider shall be unlimited.",
        "All intellectual property created shall be assigned to the company.",
    ]

    rprint("[bold]Testing embedder...[/bold]\n")

    for text in test_texts:
        vec = embed_text(text)
        rprint(f"  Text: \"{text[:60]}...\"")
        rprint(f"  Vector: [{vec[0]:.4f}, {vec[1]:.4f}, ... {vec[-1]:.4f}] ({len(vec)} dims)\n")

    rprint("[green]✓ Embedder working[/green]")