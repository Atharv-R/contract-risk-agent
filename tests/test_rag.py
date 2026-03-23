"""
Tests for the RAG pipeline: embeddings, vector store, and retrieval.
"""

import pytest
from src.rag.embedder import embed_text, embed_texts
from src.rag.store import (
    load_all_library_chunks,
    ingest_clause_library,
    get_chroma_client,
    get_or_create_collection,
)
from src.rag.retriever import retrieve_baseline, retrieve_for_risk_analysis


class TestEmbedder:
    """Test the embedding model."""

    def test_embed_single_text(self):
        vec = embed_text("This is a test sentence about liability.")
        assert len(vec) == 384, f"Expected 384 dimensions, got {len(vec)}"
        assert all(isinstance(v, float) for v in vec)
        print(f"  ✓ Single embedding: {len(vec)} dimensions")

    def test_embed_batch(self):
        texts = ["First sentence.", "Second sentence.", "Third sentence."]
        vecs = embed_texts(texts)
        assert len(vecs) == 3
        assert all(len(v) == 384 for v in vecs)
        print(f"  ✓ Batch embedding: {len(vecs)} vectors")

    def test_similar_texts_have_close_embeddings(self):
        """Sentences about the same topic should have similar vectors."""
        import numpy as np

        vec1 = embed_text("The liability shall be uncapped and unlimited.")
        vec2 = embed_text("There is no limitation on liability under this agreement.")
        vec3 = embed_text("The weather in Paris is lovely in spring.")

        # Cosine similarity (vectors are already normalized)
        sim_related = np.dot(vec1, vec2)
        sim_unrelated = np.dot(vec1, vec3)

        assert sim_related > sim_unrelated, \
            f"Related texts should be more similar ({sim_related:.3f} vs {sim_unrelated:.3f})"
        print(f"  ✓ Related similarity: {sim_related:.3f}")
        print(f"  ✓ Unrelated similarity: {sim_unrelated:.3f}")


class TestClauseLibrary:
    """Test loading and parsing the clause library."""

    def test_load_library_chunks(self):
        chunks = load_all_library_chunks()
        assert len(chunks) >= 20, f"Expected at least 20 chunks, got {len(chunks)}"
        print(f"  ✓ Loaded {len(chunks)} chunks from clause library")

    def test_chunks_have_metadata(self):
        chunks = load_all_library_chunks()
        for chunk in chunks:
            assert chunk.clause_type, "Each chunk needs a clause_type"
            assert chunk.section, "Each chunk needs a section name"
            assert chunk.text, "Each chunk needs content"
            assert len(chunk.text) > 20, "Chunks should have meaningful content"

    def test_covers_key_clause_types(self):
        chunks = load_all_library_chunks()
        clause_types = set(c.clause_type for c in chunks)

        expected = {"auto_renewal", "liability_cap", "ip_assignment", "non_compete"}
        for ct in expected:
            assert ct in clause_types, f"Missing clause type: {ct}"

        print(f"  ✓ Clause types found: {sorted(clause_types)}")


class TestVectorStore:
    """Test ChromaDB ingestion."""

    def test_ingest(self):
        count = ingest_clause_library(force_rebuild=True)
        assert count >= 20, f"Should ingest at least 20 chunks, got {count}"
        print(f"  ✓ Ingested {count} chunks")

    def test_collection_persists(self):
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        count = collection.count()
        assert count > 0, "Collection should have data after ingestion"
        print(f"  ✓ Collection has {count} chunks")


class TestRetriever:
    """Test retrieval quality."""

    @pytest.fixture(autouse=True)
    def ensure_ingested(self):
        """Make sure vector store has data before testing retrieval."""
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        if collection.count() == 0:
            ingest_clause_library(force_rebuild=True)

    def test_basic_retrieval(self):
        results = retrieve_baseline("automatic renewal clause", top_k=3)
        assert len(results) > 0, "Should return at least one result"
        assert results[0].similarity_score > 0, "Should have a positive similarity score"
        print(f"  ✓ Retrieved {len(results)} results")
        print(f"    Best match: {results[0].clause_type} ({results[0].similarity_score:.3f})")

    def test_liability_retrieval(self):
        results = retrieve_baseline(
            "Service Provider shall be liable for all damages without limitation",
            top_k=3,
        )
        clause_types = [r.clause_type for r in results]
        assert "liability_cap" in clause_types, \
            f"Should match liability. Got: {clause_types}"
        print(f"  ✓ Liability clause correctly matched")

    def test_ip_retrieval(self):
        results = retrieve_baseline(
            "All intellectual property and work product shall be assigned to Company",
            top_k=3,
        )
        clause_types = [r.clause_type for r in results]
        assert "ip_assignment" in clause_types, \
            f"Should match IP assignment. Got: {clause_types}"
        print(f"  ✓ IP assignment clause correctly matched")

    def test_non_compete_retrieval(self):
        results = retrieve_baseline(
            "Service Provider shall not compete for 36 months in North America",
            top_k=3,
        )
        clause_types = [r.clause_type for r in results]
        assert "non_compete" in clause_types, \
            f"Should match non-compete. Got: {clause_types}"
        print(f"  ✓ Non-compete clause correctly matched")

    def test_risk_analysis_retrieval(self):
        result = retrieve_for_risk_analysis(
            "This Agreement shall automatically renew for successive three year periods."
        )
        assert result["best_clause_type"] == "auto_renewal", \
            f"Should identify as auto_renewal. Got: {result['best_clause_type']}"
        assert len(result["general_matches"]) > 0
        print(f"  ✓ Risk analysis retrieval working")
        print(f"    Type: {result['best_clause_type']}")
        print(f"    Matches: {len(result['general_matches'])}")
        print(f"    Red flags: {len(result['red_flags'])}")
        print(f"    Standards: {len(result['standards'])}")

    def test_filtered_retrieval(self):
        results = retrieve_baseline(
            "termination",
            top_k=3,
            clause_type_filter="termination_convenience",
        )
        for r in results:
            assert r.clause_type == "termination_convenience", \
                f"Filter should restrict to termination. Got: {r.clause_type}"
        print(f"  ✓ Filtered retrieval working")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])