# ⚖️ ClauseGuard AI
### AI-Assisted Contract Analysis and Risk Identification System

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-00A67E)](https://langchain-ai.github.io/langgraph/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.0+-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**ClauseGuard AI** is a production-grade Generative AI and Agentic RAG application that analyses legal and business contracts (such as IT employment offer letters, residential rental agreements, and freelance contractor agreements). 

It automatically extracts critical legal clauses, identifies predatory or one-sided terms, translates legalese into plain English, drafts counter-negotiation proposals, verifies quotation authenticity against original PDF pages, answers questions via an interactive RAG chatbot, and generates downloadable audit reports in PDF, Markdown, and JSON.

---

## 🌟 Key Highlights & Dual Execution Modes

ClauseGuard AI is engineered to work in **two distinct modes**:

1. **🛡️ Offline AI Engine (Default — No API Calls Required):**
   - **Zero external API calls or API keys needed**.
   - Runs 100% locally on your machine with high-precision legal heuristic pattern matching, deterministic risk checklists, and mathematical quotation grounding verification.
   - Ideal for private, confidential contracts, evaluation, offline demos, or users without paid API subscriptions.

2. **⚡ Groq Cloud LLM Mode (Optional):**
   - Integrates with Groq API using models such as `openai/gpt-oss-20b`, `llama3-70b-8192`, or `mixtral-8x7b-32768`.
   - Simply enter your Groq API key in the sidebar to activate cloud generative intelligence.

---

## 🏗️ Architecture & Multi-Agent Workflow

```text
[ Upload PDF / Sample Contract ]
             │
             ▼
    [ PDF Page Loader ] (PyMuPDF)
             │
             ▼
    [ Text Cleaner & Chunker ] (Preserves Page Offsets)
             │
             ▼
    [ Vector Store / FAISS ] (Embeddings & Semantic Search)
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│               LangGraph Multi-Agent Pipeline            │
│                                                         │
│  1. 🤖 Clause Extractor Agent                           │
│     Extracts notice periods, bonds, termination, etc.   │
│                          │                              │
│  2. ⚠️ Risk Auditor Agent                               │
│     Scores 1-10 & assigns Low/Medium/High risk levels   │
│                          │                              │
│  3. 🤝 Negotiation Advisor Agent                        │
│     Drafts plain-English explanations & counter-wording │
│                          │                              │
│  4. 🔎 Grounding Critic Agent                           │
│     Verifies quotations against source PDF pages        │
└─────────────────────────────────────────────────────────┘
             │
             ▼
[ Streamlit Interactive Dashboard ]
  ├── 📋 Contract Audit & Scorecard
  ├── 💬 Ask Your Document (RAG Chatbot with Page Citations)
  └── 🔍 Agent Execution Trace, Pydantic JSON & Report Downloads
```

---

## 🚀 Features

- **Multi-Format PDF Ingestion:** Extracts per-page text with PyMuPDF, cleans whitespace/hyphenation, and divides text into overlapping chunks with preserved page metadata.
- **Built-in Sample Contracts:** Comes preloaded with 3 realistic agreements:
  - `it_offer_letter.pdf`: 90-day notice period, 2-year service bond ($5,000 penalty), worldwide non-compete, comprehensive IP assignment.
  - `rental_agreement.pdf`: 15% auto-renewal escalation, non-refundable deposit deductions, landlord immediate entry.
  - `freelance_contract.pdf`: Net-60 payment terms, unlimited unpaid revisions, unilateral termination, moral rights waiver.
- **Explainable Risk Checklist:** Evaluates notice periods, service bonds, exit penalties, termination, IP ownership, confidentiality, payment terms, and non-compete clauses.
- **Grounding Critic & Evidence Verification:** Every quoted clause is verified for authenticity against the source document to prevent AI hallucinations.
- **Interactive RAG Chatbot:** Ask questions about your agreement and receive instant, evidence-backed answers with page references.
- **Report Exporting:** Download comprehensive audit reports in **PDF** (via ReportLab), **Markdown (.md)**, and **JSON**.

---

## 📁 Project Directory Structure

```text
ClauseGuard-AI/
├── app.py                      # Main Streamlit application entry point
├── requirements.txt            # Python dependencies
├── README.md                   # Comprehensive documentation & guide
├── .env.example                # Example environment variables
├── .gitignore                  # Git ignore rules
│
├── .streamlit/
│   └── config.toml             # Custom theme & server settings
│
├── config/
│   ├── settings.py             # Global constants & configuration
│   └── prompts.py              # LLM system prompts for all 4 agents & RAG
│
├── data/
│   └── samples/                # Preloaded sample PDF contracts
│       ├── generate_samples.py # PDF generator script
│       ├── it_offer_letter.pdf
│       ├── rental_agreement.pdf
│       └── freelance_contract.pdf
│
├── ingestion/
│   ├── pdf_loader.py           # PyMuPDF document loader with page tracking
│   ├── text_cleaner.py         # Unicode and hyphenation normaliser
│   └── chunker.py              # Overlapping chunker with metadata
│
├── rag/
│   ├── embeddings.py           # SentenceTransformers & local vectorizer
│   ├── vector_store.py         # FAISS & NumPy cosine similarity index
│   └── retriever.py            # High-level RAG retriever
│
├── agents/
│   ├── offline_engine.py       # Zero-API deterministic legal AI engine
│   ├── clause_extractor.py     # Clause Extractor Agent
│   ├── risk_auditor.py         # Risk Auditor Agent
│   ├── negotiation_advisor.py  # Negotiation Advisor Agent
│   └── grounding_critic.py     # Grounding Critic Agent
│
├── graph/
│   ├── state.py                # LangGraph ContractAnalysisState
│   └── workflow.py             # LangGraph StateGraph pipeline
│
├── schemas/
│   ├── clause_schema.py        # Pydantic v2 clause extraction models
│   ├── risk_schema.py          # Pydantic v2 risk, negotiation, grounding models
│   └── report_schema.py        # Pydantic v2 contract report models
│
├── services/
│   ├── analysis_service.py     # Document processing orchestrator
│   ├── qa_service.py           # RAG Q&A service
│   └── report_service.py       # PDF/Markdown/JSON report builder
│
├── ui/
│   ├── components.py           # Reusable UI widgets, cards, badges
│   ├── dashboard.py            # Risk summary, scorecard, and filters
│   ├── contract_audit.py       # Main upload and analysis tab
│   ├── document_chat.py        # Ask Your Document chatbot tab
│   └── execution_trace.py      # LangGraph workflow trace and export tab
│
└── tests/
    ├── test_pdf_loader.py      # PDF loader and validator tests
    ├── test_chunker.py         # Chunking and metadata tests
    ├── test_schemas.py         # Pydantic schema validation tests
    └── test_evidence_validation.py # Evidence and quotation grounding tests
```

---

## 🛠️ Local Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/ClauseGuard-AI.git
cd ClauseGuard-AI
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*Note: If you wish to use Groq Cloud LLM mode, add your Groq API key to `.env`. Otherwise, leave it empty to use the 100% Offline AI Engine.*

### 5. Launch the Streamlit Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Unit Tests

The test suite validates PDF loading, text chunking, Pydantic schemas, and evidence grounding:

```bash
python -m pytest tests/
```

To run with verbose output:
```bash
python -m pytest tests/ -v
```

---

## ☁️ Deployment on Streamlit Community Cloud

1. Push your repository to **GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of ClauseGuard AI"
   git remote add origin https://github.com/yourusername/ClauseGuard-AI.git
   git push -u origin main
   ```
2. Navigate to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Click **"New app"** and select your `ClauseGuard-AI` repository.
4. Set the Main file path to `app.py`.
5. Under **Advanced settings > Secrets**, you can optionally add your Groq API key:
   ```toml
   GROQ_API_KEY = "gsk_..."
   DEFAULT_MODEL = "openai/gpt-oss-20b"
   ```
6. Click **Deploy!** Your application will be live in seconds.

---

## ⚖️ Legal Disclaimer

**ClauseGuard AI** provides automated, AI-assisted contract review for **informational and educational purposes only**. It does **not** constitute formal legal advice, representation, or attorney-client privilege. Always consult a licensed attorney or legal professional before signing or negotiating legal contracts.
