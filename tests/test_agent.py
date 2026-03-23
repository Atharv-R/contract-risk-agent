"""
Tests for the full agent pipeline.

This test makes REAL API calls to Gemini, so it:
  - Takes about 60-90 seconds to run
  - Requires GEMINI_API_KEY in your .env file
  - Prints progress so you know it's not frozen
"""

import pytest
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SAMPLE_PDF = "data/sample_contracts/sample_msa_risky.pdf"
HAS_API_KEY = bool(os.getenv("GEMINI_API_KEY"))


@pytest.mark.skipif(not HAS_API_KEY, reason="GEMINI_API_KEY not set")
class TestAgentPipeline:
    """Integration tests for the full contract analysis pipeline."""

    @pytest.fixture(scope="class")
    def report(self):
        """
        Run the full pipeline ONCE and share the result across all tests.
        This avoids making duplicate API calls.
        """
        from src.agent.graph import analyze_contract

        assert Path(SAMPLE_PDF).exists(), (
            f"Sample contract not found at {SAMPLE_PDF}. "
            f"Run: python scripts/create_sample_contract.py"
        )

        print("\n\n🚀 Running full agent pipeline (this takes ~60-90 seconds)...\n")
        result = analyze_contract(SAMPLE_PDF)
        return result

    def test_report_has_overall_score(self, report):
        """Report should include an overall risk score between 0 and 1."""
        assert "overall_risk_score" in report
        score = report["overall_risk_score"]
        assert 0.0 <= score <= 1.0, f"Score out of range: {score}"
        print(f"  ✓ Overall risk score: {score}")

    def test_report_has_risk_level(self, report):
        """Report should classify risk as low/medium/high/critical."""
        assert "overall_risk_level" in report
        level = report["overall_risk_level"]
        assert level in ("low", "medium", "high", "critical"), f"Invalid level: {level}"
        print(f"  ✓ Overall risk level: {level}")

    def test_report_has_executive_summary(self, report):
        """Report should include a readable executive summary."""
        summary = report.get("executive_summary", "")
        assert len(summary) > 50, "Executive summary too short"
        print(f"  ✓ Executive summary: {len(summary)} chars")

    def test_report_has_clause_analyses(self, report):
        """Should have analyzed multiple clauses."""
        analyses = report.get("clause_analyses", [])
        assert len(analyses) >= 3, f"Only {len(analyses)} clauses analyzed"
        print(f"  ✓ Clauses analyzed: {len(analyses)}")

    def test_clause_analyses_have_structure(self, report):
        """Each clause analysis should have the expected fields."""
        required_fields = ["risk_score", "risk_level", "section_id"]

        for analysis in report.get("clause_analyses", []):
            for field in required_fields:
                assert field in analysis, (
                    f"Clause {analysis.get('section_id', '?')} missing field: {field}"
                )

        print(f"  ✓ All clause analyses have required fields")

    def test_detects_high_risk_clauses(self, report):
        """Our sample contract has intentionally risky clauses — should flag them."""
        high_risk = [
            a for a in report.get("clause_analyses", [])
            if a.get("risk_level") in ("high", "critical")
        ]
        assert len(high_risk) >= 2, (
            f"Should find at least 2 high/critical risk clauses. Found {len(high_risk)}"
        )
        print(f"  ✓ High/critical risk clauses found: {len(high_risk)}")

        for a in high_risk:
            print(f"    → {a.get('section_id', '?')} "
                  f"{a.get('section_title', '?')}: "
                  f"{a.get('risk_level', '?').upper()} ({a.get('risk_score', '?')})")

    def test_has_recommendation(self, report):
        """Report should include an overall recommendation."""
        rec = report.get("overall_recommendation", "")
        assert len(rec) > 0, "Should have a recommendation"
        print(f"  ✓ Recommendation: {rec}")

    def test_has_parties(self, report):
        """Should identify contract parties."""
        parties = report.get("parties", [])
        assert len(parties) >= 1, "Should identify at least one party"
        print(f"  ✓ Parties: {parties[:4]}")

    def test_report_summary(self, report):
        """Print a full summary of the report for visual inspection."""
        print(f"\n  {'═' * 50}")
        print(f"  CONTRACT: {report.get('contract_name', '?')}")
        print(f"  RISK:     {report.get('overall_risk_level', '?').upper()} ({report.get('overall_risk_score', '?')})")
        print(f"  CLAUSES:  {report.get('clause_count', '?')} analyzed, {report.get('high_risk_count', '?')} high risk")
        print(f"  ACTION:   {report.get('overall_recommendation', '?').upper()}")
        print(f"  {'═' * 50}")

        if report.get("negotiation_points"):
            print(f"\n  Negotiation Points:")
            for p in report["negotiation_points"][:5]:
                print(f"    → {p}")


class TestLLMConnection:
    """Quick test that the LLM wrapper works."""

    @pytest.mark.skipif(not HAS_API_KEY, reason="GEMINI_API_KEY not set")
    def test_gemini_responds(self):
        from src.agent.llm import call_gemini, parse_json_response

        response = call_gemini(
            prompt='Respond with exactly: {"test": true}',
            system_prompt="Respond only with valid JSON.",
        )
        parsed = parse_json_response(response)
        assert "test" in parsed or "error" not in parsed
        print(f"  ✓ Gemini responded successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])