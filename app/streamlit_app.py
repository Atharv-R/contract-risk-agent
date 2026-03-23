"""
Contract Risk Agent — Streamlit Dashboard

Upload a contract PDF → Watch the AI analyze it → Get a scored risk report.

Run with:  streamlit run app/streamlit_app.py
"""
import warnings
import os
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sys
from pathlib import Path

# Make sure project root is in Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import tempfile
import json
from datetime import datetime


# ── Page Config (must be first Streamlit call) ───────────────────

st.set_page_config(
    page_title="Contract Risk Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Custom CSS ───────────────────────────────────────────────────

st.markdown("""
<style>
    .risk-critical { color: #DC2626; font-weight: bold; font-size: 1.1em; }
    .risk-high { color: #EA580C; font-weight: bold; font-size: 1.1em; }
    .risk-medium { color: #CA8A04; font-weight: bold; font-size: 1.1em; }
    .risk-low { color: #16A34A; font-weight: bold; font-size: 1.1em; }

    .big-score {
        font-size: 3em;
        font-weight: bold;
        text-align: center;
        padding: 10px;
        border-radius: 10px;
        margin: 10px 0;
    }

    .stExpander { border-left: 3px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────

with st.sidebar:
    st.title("🔍 Contract Risk Agent")
    st.markdown("---")
    st.markdown(
        "AI-powered contract analysis that identifies risky clauses, "
        "compares them against industry standards, and generates "
        "a plain-English risk report."
    )
    st.markdown("---")

    st.markdown("**How it works:**")
    st.markdown("""
    1. 📄 Upload a contract PDF
    2. 🤖 AI parses and analyzes every clause
    3. 📊 RAG compares against standard baselines
    4. ⚖️ Each clause gets a risk score
    5. 📋 Download a detailed risk report
    """)

    st.markdown("---")
    st.markdown("**Tech Stack:**")
    st.markdown("""
    - 🧠 LLM: Groq (Llama 3.3 70B)
    - 🔎 RAG: ChromaDB + Sentence Transformers
    - 📄 PDF: pdfplumber + PyMuPDF
    - 🏷️ NER: spaCy
    - 🔄 Agent: LangGraph
    """)

    st.markdown("---")
    st.caption("Built with ❤️ as an AI/ML portfolio project")


# ── Helper Functions ─────────────────────────────────────────────

def risk_color(level: str) -> str:
    return {
        "critical": "#DC2626",
        "high": "#EA580C",
        "medium": "#CA8A04",
        "low": "#16A34A",
    }.get(level.lower(), "#6B7280")


def risk_emoji(level: str) -> str:
    return {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
    }.get(level.lower(), "⚪")


# ── Session State Initialization ─────────────────────────────────

if "report" not in st.session_state:
    st.session_state.report = None
if "analyzing" not in st.session_state:
    st.session_state.analyzing = False


# ── Main Content ─────────────────────────────────────────────────

st.title("⚖️ Contract Risk Analysis")
st.markdown("Upload a contract PDF and get an instant AI-powered risk assessment.")

# ── File Upload ──────────────────────────────────────────────────

uploaded_file = st.file_uploader(
    "Upload a contract PDF",
    type=["pdf"],
    help="Upload any contract PDF — MSAs, NDAs, SaaS agreements, employment contracts, etc.",
)

if uploaded_file:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"📄 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
    with col2:
        analyze_btn = st.button("🚀 Analyze Contract", type="primary", use_container_width=True)
else:
    analyze_btn = False
    st.info("👆 Upload a contract PDF to get started. A sample risky MSA is included in `data/sample_contracts/`.")

# ── Analysis ─────────────────────────────────────────────────────

if analyze_btn and uploaded_file:
    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    # Run the analysis with a status display
    with st.status("🤖 Analyzing contract...", expanded=True) as status:
        st.write("📄 **Step 1/5:** Parsing document and splitting into clauses...")

        try:
            from src.agent.graph import analyze_contract

            report = analyze_contract(tmp_path)
            st.session_state.report = report

            status.update(label="✅ Analysis complete!", state="complete", expanded=False)

        except Exception as e:
            status.update(label="❌ Analysis failed", state="error")
            st.error(f"Error during analysis: {str(e)}")
            st.session_state.report = None

    # Clean up temp file
    Path(tmp_path).unlink(missing_ok=True)


# ── Display Results ──────────────────────────────────────────────

report = st.session_state.report

if report:
    st.markdown("---")

    # ── Score Cards Row ──────────────────────────────────────────
    overall_level = report.get("overall_risk_level", "medium")
    overall_score = report.get("overall_risk_score", 0.5)
    color = risk_color(overall_level)
    emoji = risk_emoji(overall_level)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""<div style="text-align:center; padding:15px; background: linear-gradient(135deg, {color}22, {color}11); border-radius:10px; border: 2px solid {color};">
                <div style="font-size:2.5em; font-weight:bold; color:{color};">{overall_score}</div>
                <div style="font-size:0.9em; color:{color};">{emoji} {overall_level.upper()} RISK</div>
            </div>""",
            unsafe_allow_html=True,
        )

    with col2:
        st.metric("Clauses Analyzed", report.get("clause_count", 0))

    with col3:
        st.metric("High/Critical Risks", report.get("high_risk_count", 0))

    with col4:
        recommendation = report.get("overall_recommendation", "review").upper()
        rec_colors = {"SIGN": "🟢", "NEGOTIATE": "🟡", "REJECT": "🔴", "REVIEW": "🟠"}
        st.metric("Recommendation", f"{rec_colors.get(recommendation, '⚪')} {recommendation}")

    st.markdown("---")

    # ── Executive Summary ────────────────────────────────────────
    exec_summary = report.get("executive_summary", "")
    if exec_summary:
        st.subheader("📋 Executive Summary")
        st.markdown(exec_summary)
        st.markdown("")

    # ── Tabs ─────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "⚖️ Clause Analysis",
        "⚠️ Missing Clauses",
        "🎯 Negotiation Points",
        "📊 Full Data",
    ])

    # ── Tab 1: Clause Analysis ───────────────────────────────────
    with tab1:
        st.subheader("Clause-by-Clause Risk Breakdown")

        # Sort: highest risk first
        analyses = sorted(
            report.get("clause_analyses", []),
            key=lambda x: x.get("risk_score", 0),
            reverse=True,
        )

        for a in analyses:
            level = a.get("risk_level", "medium")
            score = a.get("risk_score", 0.5)
            section = a.get("section_title", a.get("section_id", "Unknown"))
            emoji = risk_emoji(level)
            color = risk_color(level)

            with st.expander(
                f"{emoji} **{a.get('section_id', '?')}. {section}** — "
                f"{level.upper()} ({score})",
                expanded=(level in ("critical", "high")),
            ):
                # Risk badge
                st.markdown(
                    f'<span style="background:{color}; color:white; padding:3px 12px; '
                    f'border-radius:12px; font-size:0.85em; font-weight:bold;">'
                    f'{level.upper()} RISK — Score: {score}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("")

                clause_type = a.get("clause_type", "general")
                st.markdown(f"**Clause Type:** `{clause_type}`")

                summary = a.get("summary", "")
                if summary:
                    st.markdown(f"**Summary:** {summary}")

                plain = a.get("plain_english", "")
                if plain:
                    st.info(f"💡 **What this means:** {plain}")

                risks = a.get("risks_found", [])
                if risks:
                    st.markdown("**Risks Found:**")
                    for r in risks:
                        st.markdown(f"- ⚠️ {r}")

                red_flags = a.get("red_flags", [])
                if red_flags:
                    st.markdown("**Red Flags:**")
                    for rf in red_flags:
                        st.markdown(f"- 🚩 {rf}")

                rec = a.get("recommendation", "")
                if rec:
                    st.success(f"💡 **Recommendation:** {rec}")

    # ── Tab 2: Missing Clauses ───────────────────────────────────
    with tab2:
        missing = report.get("missing_clauses", [])
        if missing:
            st.subheader(f"⚠️ {len(missing)} Missing Clause(s) Detected")
            for m in missing:
                importance = m.get("importance", "medium")
                emoji = "🔴" if importance == "high" else "🟡"
                clause_type = m.get("clause_type", "Unknown").replace("_", " ").title()

                st.warning(
                    f"{emoji} **{clause_type}** (Importance: {importance.upper()})\n\n"
                    f"{m.get('plain_english', 'No details available.')}"
                )
        else:
            st.success("✅ No critical missing clauses detected.")

    # ── Tab 3: Negotiation Points ────────────────────────────────
    with tab3:
        points = report.get("negotiation_points", [])
        top_issues = report.get("top_issues", [])

        if top_issues:
            st.subheader("🎯 Top Issues to Address")
            for i, issue in enumerate(top_issues, 1):
                severity = issue.get("severity", "medium")
                emoji = risk_emoji(severity)
                st.markdown(
                    f"**{i}. {emoji} {issue.get('issue', 'Issue')}** "
                    f"({severity.upper()})"
                )
                action = issue.get("action", "")
                if action:
                    st.markdown(f"   → Action: {action}")
                st.markdown("")

        if points:
            st.subheader("📝 Specific Negotiation Points")
            for i, point in enumerate(points, 1):
                st.markdown(f"{i}. {point}")
        elif not top_issues:
            st.info("No specific negotiation points generated.")

    # ── Tab 4: Full Data ─────────────────────────────────────────
    with tab4:
        st.subheader("📊 Raw Analysis Data")
        st.json(report)

    # ── Download Section ─────────────────────────────────────────
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        try:
            from src.report.pdf_export import generate_pdf_report
            pdf_bytes = generate_pdf_report(report)

            contract_stem = report.get("contract_name", "contract").replace(".pdf", "")
            st.download_button(
                label="📥 Download PDF Report",
                data=pdf_bytes,
                file_name=f"risk_report_{contract_stem}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")
            st.info("You can still download the JSON report below.")

    with col2:
        json_bytes = json.dumps(report, indent=2, default=str).encode()
        contract_stem = report.get("contract_name", "contract").replace(".pdf", "")
        st.download_button(
            label="📥 Download JSON Data",
            data=json_bytes,
            file_name=f"risk_report_{contract_stem}.json",
            mime="application/json",
            use_container_width=True,
        )