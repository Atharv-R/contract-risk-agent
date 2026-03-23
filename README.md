# Contract Risk Agent

**Agentic AI Contract Risk Analysis that identifies risky clauses, compares them against industry baselines, and generates plain-English risk reports.**

Every company signs contracts. Almost none have intelligent clause analysis. Enterprise solutions like Ironclad cost six figures. This project brings that capability to anyone — for free.

Upload a contract PDF and then watch the AI agent analyze every clause. Get a scored risk report with actionable recommendations.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![LLM](https://img.shields.io/badge/LLM-Llama_3.3_70B-orange)
![RAG](https://img.shields.io/badge/RAG-ChromaDB-purple)

---

##  What It Does:

| Feature | Description |
|---|---|
| **PDF Parsing** | Extracts text from any contract PDF with fallback OCR |
| **Clause Detection** | Splits contracts into individual clauses using legal structure patterns |
| **Named Entity Recognition** | Identifies parties, dates, dollar amounts, jurisdictions, and legal terms |
| **RAG Baseline Comparison** | Compares each clause against a curated library of standard/acceptable terms |
| **LLM Risk Analysis** | Scores each clause 0.0–1.0 with plain-English explanations |
| **Missing Clause Detection** | Flags important protections that are absent from the contract |
| **Risk Report Generation** | Downloadable PDF report with executive summary and negotiation points |
| **Interactive Dashboard** | Clean Streamlit UI: upload, analyze, review, download |

### Risk Categories Analyzed

🔴 **Auto-Renewal** · **Uncapped Liability** · **IP Assignment** · **Non-Compete**
🟡 **Indemnification** · **Termination** · **Governing Law** · **Confidentiality**
🟢 **Payment Terms** · **Force Majeure**

---


## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| PDF Parsing | pdfplumber + PyMuPDF | Text extraction from contracts |
| NER | spaCy | Extract parties, dates, money, jurisdictions |
| Embeddings | sentence-transformers (MiniLM) | Local vector embeddings (384-dim) |
| Vector Store | ChromaDB | Persistent RAG storage for clause library |
| LLM | Groq (Llama 3.3 70B) / Google Gemini | Clause risk analysis and report generation |
| Agent Framework | LangGraph | State machine orchestrating the analysis pipeline |
| Frontend | Streamlit | Interactive dashboard |
| Report Export | fpdf2 | Professional PDF risk reports |

**Total cost: $0** : all free-tier APIs and local models.

---

## Quick Start

### Prerequisites
- Python 3.10 or higher
- A free API key from [Groq](https://console.groq.com/keys) (takes 30 seconds)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/contract-risk-agent.git
cd contract-risk-agent

# 2. Create virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# 3. Install dependencies
conda install -c conda-forge hnswlib
conda install -c conda-forge pytesseract
pip install -r requirements-safe.txt
pip install chromadb --no-build-isolation --prefer-binary
pip install torch torchvision torchaudio
pip install sentence-transformers
pip install spacy
python -m spacy download en_core_web_sm
pip check

# 4. Configure API key
# IMPORTANT!! Edit .env and add your GROQ_API_KEY
# The API key in the env file is a placeholder
cp .env.example .env

# 5. Build the vector store (one-time, takes ~10 seconds)
python -m src.rag.store

# 6. Generate a sample contract for testing
python scripts/create_sample_contract.py

# 7. Launch the dashboard
streamlit run app/streamlit_app.py

# COMMAND LINE USAGE:
# Analyze a contract from the terminal (no UI)
python -m src.agent.graph

# Run tests
pytest tests/ -v


#PROJECT STRUCTURE
contract-risk-agent/
├── app/
│   └── streamlit_app.py          # Dashboard UI
├── clause_library/                # RAG knowledge base (10 clause types)
│   ├── auto_renewal.md
│   ├── liability_cap.md
│   ├── ip_assignment.md
│   └── ...
├── config/
│   ├── settings.py                # Pydantic configuration
│   └── risk_categories.yaml       # Risk taxonomy
├── src/
│   ├── parser/
│   │   ├── pdf_extractor.py       # PDF → raw text
│   │   └── clause_chunker.py      # Text → clause-level chunks
│   ├── ner/
│   │   └── legal_ner.py           # Named entity recognition
│   ├── rag/
│   │   ├── embedder.py            # Sentence-transformer embeddings
│   │   ├── store.py               # ChromaDB vector store
│   │   └── retriever.py           # Baseline retrieval
│   ├── agent/
│   │   ├── llm.py                 # Multi-provider LLM wrapper
│   │   ├── state.py               # LangGraph state schema
│   │   ├── prompts.py             # Analysis prompt templates
│   │   ├── nodes.py               # Pipeline step functions
│   │   └── graph.py               # LangGraph assembly
│   └── report/
│       └── pdf_export.py          # PDF report generation
├── tests/                         # Test suite
├── scripts/
│   └── create_sample_contract.py  # Generate test PDF
├── requirements.txt
├── .env.example
└── README.md
