"""
Tests for the PDF extraction and clause chunking pipeline.
"""

from pathlib import Path
from src.parser.pdf_extractor import extract_pdf
from src.parser.clause_chunker import chunk_contract, ClauseChunk


SAMPLE_PDF = "data/sample_contracts/sample_msa_risky.pdf"


class TestPDFExtractor:
    """Tests for pdf_extractor.py"""

    def test_extract_returns_document(self):
        """Should return an ExtractedDocument with content."""
        doc = extract_pdf(SAMPLE_PDF)

        assert doc.filename == "sample_msa_risky.pdf"
        assert doc.total_pages > 0
        assert len(doc.full_text) > 500
        print(f"  ✓ Extracted {doc.total_pages} pages, {len(doc.full_text)} chars")

    def test_extract_has_metadata(self):
        """Should include extraction metadata."""
        doc = extract_pdf(SAMPLE_PDF)

        assert "extraction_method" in doc.metadata
        assert "total_characters" in doc.metadata
        assert doc.metadata["total_characters"] > 0

    def test_extract_finds_key_terms(self):
        """Should contain expected legal terms from our sample contract."""
        doc = extract_pdf(SAMPLE_PDF)
        text_lower = doc.full_text.lower()

        expected_terms = [
            "agreement",
            "intellectual property",
            "auto",       # auto-renewal variations
            "liability",
            "non-compete",
            "indemnif",   # indemnify / indemnification
            "governing law",
        ]

        for term in expected_terms:
            assert term in text_lower, f"Expected to find '{term}' in contract text"
            print(f"  ✓ Found: '{term}'")

    def test_file_not_found(self):
        """Should raise FileNotFoundError for missing files."""
        try:
            extract_pdf("nonexistent.pdf")
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            print("  ✓ Correctly raised FileNotFoundError")


class TestClauseChunker:
    """Tests for clause_chunker.py"""

    def test_chunk_finds_sections(self):
        """Should detect sections from our sample contract."""
        doc = extract_pdf(SAMPLE_PDF)
        chunks = chunk_contract(doc.full_text)

        assert len(chunks) >= 5, f"Expected at least 5 chunks, got {len(chunks)}"
        print(f"  ✓ Found {len(chunks)} clause chunks")

    def test_chunks_have_content(self):
        """Each chunk should have meaningful text."""
        doc = extract_pdf(SAMPLE_PDF)
        chunks = chunk_contract(doc.full_text)

        for chunk in chunks:
            assert isinstance(chunk, ClauseChunk)
            assert len(chunk.text) > 20, f"Chunk too short: {chunk.text[:50]}"

        print(f"  ✓ All {len(chunks)} chunks have content")

    def test_chunks_are_ordered(self):
        """Chunks should be in document order."""
        doc = extract_pdf(SAMPLE_PDF)
        chunks = chunk_contract(doc.full_text)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
        print(f"  ✓ Chunks are properly ordered")

    def test_chunk_previews(self):
        """Print chunk previews for manual inspection."""
        doc = extract_pdf(SAMPLE_PDF)
        chunks = chunk_contract(doc.full_text)

        print(f"\n  {'#':<4} {'Section':<15} {'Title':<30} {'Chars':<8}")
        print(f"  {'─'*4} {'─'*15} {'─'*30} {'─'*8}")
        for c in chunks:
            title = c.section_title[:28] if c.section_title else "(untitled)"
            print(f"  {c.chunk_index:<4} {c.section_id:<15} {title:<30} {c.char_count:<8}")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])