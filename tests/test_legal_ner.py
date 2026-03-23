"""
Tests for the legal NER pipeline.
"""

from src.ner.legal_ner import extract_entities, extract_entities_from_chunks, get_contract_summary
from src.parser.pdf_extractor import extract_pdf
from src.parser.clause_chunker import chunk_contract


SAMPLE_PDF = "data/sample_contracts/sample_msa_risky.pdf"


class TestEntityExtraction:
    """Test entity extraction on known text."""

    def test_finds_parties(self):
        """Should detect company names."""
        text = """
        This Agreement is between Nexus Dynamics Inc., a Delaware corporation,
        and Brightpath Solutions LLC, a California company.
        """
        entities = extract_entities(text)

        party_texts = [e.text.lower() for e in entities.parties]
        # At least one of these should be found
        found = any(
            "nexus" in t or "brightpath" in t
            for t in party_texts
        )
        assert found, f"Expected to find company names. Got: {party_texts}"
        print(f"  ✓ Found parties: {[e.text for e in entities.parties]}")

    def test_finds_dates(self):
        """Should detect dates."""
        text = "This Agreement is effective as of January 15, 2025 and expires December 31, 2026."
        entities = extract_entities(text)

        assert len(entities.dates) >= 1, "Should find at least one date"
        print(f"  ✓ Found dates: {[e.text for e in entities.dates]}")

    def test_finds_durations(self):
        """Should detect time periods like '12 months' and 'thirty-six (36) months'."""
        text = """
        The initial term is twenty-four (24) months. The non-compete lasts
        for thirty-six (36) months. Notice must be given 90 days prior.
        """
        entities = extract_entities(text)

        assert len(entities.durations) >= 2, f"Should find at least 2 durations. Got: {[e.text for e in entities.durations]}"
        print(f"  ✓ Found durations: {[e.text for e in entities.durations]}")

    def test_finds_money(self):
        """Should detect dollar amounts."""
        text = "Company's liability shall not exceed $150,000. The total contract value is $500,000."
        entities = extract_entities(text)

        assert len(entities.money) >= 1, "Should find at least one money amount"
        print(f"  ✓ Found money: {[e.text for e in entities.money]}")

    def test_finds_jurisdictions(self):
        """Should detect states and geographic references."""
        text = "This Agreement shall be governed by the laws of the State of Delaware."
        entities = extract_entities(text)

        jurisdiction_texts = [e.text.lower() for e in entities.jurisdictions]
        assert any("delaware" in t for t in jurisdiction_texts), \
            f"Should find Delaware. Got: {jurisdiction_texts}"
        print(f"  ✓ Found jurisdictions: {[e.text for e in entities.jurisdictions]}")

    def test_finds_percentages(self):
        """Should detect percentage values."""
        text = "Late payments accrue interest at 1.5% per month."
        entities = extract_entities(text)

        assert len(entities.percentages) >= 1, "Should find at least one percentage"
        print(f"  ✓ Found percentages: {[e.text for e in entities.percentages]}")

    def test_finds_legal_terms(self):
        """Should detect key legal concepts."""
        text = """
        The agreement includes automatic renewal provisions.
        Service Provider shall indemnify and hold harmless the Company.
        All intellectual property shall be assigned. Binding arbitration
        shall apply. The non-compete restricts competitive activities.
        """
        entities = extract_entities(text)

        term_texts = [e.text.lower() for e in entities.legal_terms]
        expected = ["automatic renewal", "intellectual property", "binding arbitration"]
        for term in expected:
            assert any(term in t for t in term_texts), \
                f"Should find '{term}'. Got: {term_texts}"
        print(f"  ✓ Found {len(entities.legal_terms)} legal terms")

    def test_deduplication(self):
        """Same entity at same position shouldn't appear twice."""
        text = "Nexus Dynamics Inc. and Nexus Dynamics Inc. agree to the following."
        entities = extract_entities(text)

        # Should have entities but not excessive duplicates
        all_ents = entities.all_entities
        assert len(all_ents) < 50, f"Too many entities ({len(all_ents)}), dedup might be broken"
        print(f"  ✓ Deduplication working: {len(all_ents)} total entities")


class TestFullPipeline:
    """Test NER on actual PDF extraction output."""

    def test_ner_on_sample_contract(self):
        """Run full pipeline: PDF → chunks → NER on each chunk."""
        doc = extract_pdf(SAMPLE_PDF)
        chunks = chunk_contract(doc.full_text)
        results = extract_entities_from_chunks(chunks)

        aggregated = results["aggregated"]
        summary = get_contract_summary(aggregated)

        print(f"\n  Full Pipeline Results:")
        print(f"  {'─' * 40}")
        print(f"  Parties:       {summary['parties'][:5]}")
        print(f"  Dates:         {summary['key_dates'][:5]}")
        print(f"  Durations:     {summary['time_periods'][:5]}")
        print(f"  Money:         {summary['financial_values'][:5]}")
        print(f"  Jurisdictions: {summary['jurisdictions'][:5]}")
        print(f"  Legal Terms:   {len(summary['key_legal_concepts'])} found")
        print(f"  {'─' * 40}")
        print(f"  Total entities: {summary['entity_counts']['total']}")

        # Basic sanity checks
        assert summary["entity_counts"]["total"] > 10, "Should find many entities in a full contract"
        assert len(summary["parties"]) >= 1, "Should find at least one party"
        assert len(summary["key_legal_concepts"]) >= 3, "Should find key legal concepts"

    def test_per_chunk_entities(self):
        """Each chunk should have its own entity set."""
        doc = extract_pdf(SAMPLE_PDF)
        chunks = chunk_contract(doc.full_text)
        results = extract_entities_from_chunks(chunks)

        chunks_with_entities = sum(
            1 for ce in results["by_chunk"].values()
            if len(ce.all_entities) > 0
        )

        assert chunks_with_entities >= 3, "At least 3 chunks should have entities"
        print(f"  ✓ {chunks_with_entities}/{len(chunks)} chunks have entities")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])