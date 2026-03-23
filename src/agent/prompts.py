"""
Prompts — All LLM prompt templates for the contract risk agent.

These are the instructions that tell Gemini HOW to analyze contracts.
The quality of these prompts directly determines the quality of the analysis.
"""

# ── System Prompts ───────────────────────────────────────────────

CLAUSE_ANALYSIS_SYSTEM = """You are an expert contract attorney specializing in risk analysis for businesses.

Your job: Analyze a specific contract clause, compare it against standard industry practices, and produce a clear risk assessment.

Rules:
1. Be specific — cite exact phrases from the clause that create risk.
2. Score conservatively — only flag genuine risks, not standard boilerplate.
3. Explain in plain English — the reader is a business owner, not a lawyer.
4. Always suggest concrete alternatives or negotiation points.
5. Respond ONLY with the requested JSON format. No extra text."""


MISSING_CLAUSES_SYSTEM = """You are an expert contract attorney reviewing a contract for completeness.

Your job: Given a list of clause types found in a contract, identify important protections that are MISSING.

Rules:
1. Only flag genuinely important missing clauses — not nice-to-haves.
2. Explain WHY each missing clause matters in plain English.
3. Respond ONLY with the requested JSON format. No extra text."""


EXECUTIVE_SUMMARY_SYSTEM = """You are an expert contract attorney writing a risk briefing for a business executive.

Your job: Synthesize clause-level analyses into a clear, actionable executive summary.

Rules:
1. Lead with the bottom line: is this contract safe to sign, risky, or dangerous?
2. Highlight the top 3 most critical issues.
3. Use plain English — no legal jargon without explanation.
4. Keep it to 2-3 paragraphs.
5. Respond ONLY with the requested JSON format. No extra text."""


# ── User Prompt Templates ────────────────────────────────────────

CLAUSE_ANALYSIS_PROMPT = """Analyze this contract clause against the baseline knowledge provided.

## CONTRACT CLAUSE
Section: {section_id} — {section_title}
{clause_text}

## BASELINE KNOWLEDGE (what's standard/acceptable for this type of clause)
{baseline_context}

## ENTITIES DETECTED IN THIS CLAUSE
{entities_summary}

## INSTRUCTIONS
Compare this clause against the baseline. Identify specific risks, red flags, and deviations from standard practice.

Respond with this exact JSON structure:
{{
    "clause_type": "one of: auto_renewal, liability_cap, ip_assignment, non_compete, indemnification, termination, confidentiality, governing_law, force_majeure, payment_terms, general",
    "risk_score": 0.0 to 1.0 where 0=safe and 1=dangerous,
    "risk_level": "low or medium or high or critical",
    "summary": "One sentence: what does this clause do?",
    "risks_found": ["List each specific risk identified"],
    "red_flags": ["List exact red flag phrases or concepts found"],
    "plain_english": "2-3 sentence explanation a non-lawyer can understand. What does this mean for someone signing this contract?",
    "recommendation": "Specific suggestion: what should be negotiated or changed?"
}}

Risk scoring guide:
- 0.0-0.3 (low): Standard clause, no significant concerns
- 0.3-0.6 (medium): Some unfavorable terms, worth negotiating
- 0.6-0.8 (high): Significantly unfavorable, should push back
- 0.8-1.0 (critical): Dangerous terms, do not sign without changes"""


MISSING_CLAUSES_PROMPT = """Review what clause types were found in this contract and identify important MISSING protections.

## CLAUSE TYPES FOUND IN THE CONTRACT
{found_types}

## PARTIES
{parties}

## INSTRUCTIONS
A well-drafted contract should typically include protections for: liability limitation, termination rights, confidentiality, governing law/dispute resolution, force majeure, indemnification, and IP ownership (if applicable).

Identify any important clause types that appear to be MISSING from this contract.

Respond with this exact JSON structure:
{{
    "missing_clauses": [
        {{
            "clause_type": "name of the missing clause type",
            "importance": "high or medium",
            "plain_english": "Why this matters and what risk it creates"
        }}
    ]
}}

Only include genuinely important missing clauses. If the contract is comprehensive, return an empty list."""


EXECUTIVE_SUMMARY_PROMPT = """Write an executive risk summary for this contract.

## CONTRACT OVERVIEW
Parties: {parties}
Key Dates: {key_dates}
Total Clauses Analyzed: {clause_count}

## CLAUSE-LEVEL RISK SCORES
{clause_summaries}

## MISSING CLAUSES
{missing_summary}

## OVERALL RISK SCORE: {overall_score} ({overall_level})

## INSTRUCTIONS
Write a concise executive summary covering:
1. Overall assessment — is this contract favorable, balanced, or risky?
2. The top 3 most critical issues that need attention.
3. A clear recommendation: sign as-is, negotiate specific terms, or walk away.

Respond with this exact JSON structure:
{{
    "executive_summary": "2-3 paragraph summary in plain English",
    "top_issues": [
        {{
            "issue": "Brief description",
            "severity": "critical or high or medium",
            "action": "What to do about it"
        }}
    ],
    "overall_recommendation": "sign / negotiate / reject",
    "negotiation_points": ["List the specific terms to push back on"]
}}"""