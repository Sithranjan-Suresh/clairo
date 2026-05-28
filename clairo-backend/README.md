# CLAIRO

CLAIRO is an AI-native denial intelligence platform built for specialty healthcare providers. It gives medical practices two things at the same time: the ability to predict insurance claim denials before they happen, and the ability to automatically generate citation-backed appeal letters when they do — using the payer's own policy documentation as evidence.

---

## Features

- **PDF Upload & Extraction** — Upload a denial letter PDF; raw text is extracted via PyMuPDF
- **Structured Claim Extraction** — LLM parses the text into payer, patient ID, CPT codes, denial reason, billed/denied amounts, and service date
- **Denial Classification** — Categorizes denials into: `medical_necessity`, `prior_authorization`, `coding_mismatch`, `eligibility`, `documentation_gap`, or `timely_filing`
- **RAG Policy Retrieval** — Queries a ChromaDB vector store of real payer policy PDFs with a custom reranker that prioritizes clinical criteria sections over boilerplate
- **Appeal Letter Generation** — Produces a structured, citation-backed appeal letter referencing real payer policy documents by name and effective date
- **Chained Appeal Endpoint** — Accepts real upload output directly, fully connecting the upload-to-appeal pipeline
- **Appeal Viability Scoring** — Rates each appeal as High, Medium, or Low viability with an expected recovery probability range
- **PDF Export** — Generates a formatted, submission-ready PDF with claim header and AI-assisted disclaimer
- **Pre-Submission Risk Scoring** — Hybrid rule-based and LLM scoring producing a 0–100 denial risk score with specific remediation advice
- **Claim Queue Scoring** — Score a batch of claims at once, returned sorted by risk score descending
- **Denial Pattern Dashboard** — Five analytics endpoints with practice vs. industry benchmark comparison; every real upload feeds the dashboard automatically
- **Voice AI** — Accepts audio input, transcribes via Groq Whisper, extracts intent, and routes to the correct endpoint automatically
- **MCP Server** — Full Model Context Protocol wrapper exposing all CLAIRO tools so AI agents can autonomously orchestrate the complete denial-to-appeal pipeline

---

## Project Structure

```
clairo-main/
├── app/
│   ├── main.py                        # FastAPI app entry point
│   ├── database.py                    # SQLite setup via SQLAlchemy
│   ├── models.py                      # DenialClaim ORM model
│   ├── schemas.py
│   ├── data/policies/                 # Payer policy PDFs for RAG ingestion
│   ├── uploads/                       # Uploaded denial letter PDFs
│   ├── rag/
│   │   ├── embedder.py                # Lazy-loaded sentence-transformers model
│   │   ├── ingest.py                  # Loads policy PDFs into ChromaDB
│   │   ├── loader.py                  # PDF text chunking
│   │   ├── retriever.py               # Semantic search + custom reranker
│   │   └── vectorstore.py             # ChromaDB persistent client
│   ├── routes/
│   │   ├── upload.py                  # POST /upload
│   │   ├── rag.py                     # GET /rag/retrieve
│   │   ├── appeal.py                  # POST /appeal/generate-appeal, /appeal/generate-from-claim
│   │   ├── risk.py                    # POST /risk/score-claim, /risk/score-queue
│   │   ├── export.py                  # POST /export/export-pdf, /export/viability
│   │   ├── analytics.py              # GET /analytics/*, POST /analytics/seed
│   │   └── voice.py                  # POST /voice/process
│   └── services/
│       ├── groq_services.py           # Groq client initialization
│       ├── extraction_service.py      # Structured claim extraction
│       ├── classification_service.py  # Denial classification
│       ├── appeal_service.py          # Appeal generation + viability scoring
│       ├── risk_service.py            # Hybrid risk scoring
│       ├── pdf_service.py             # PyMuPDF text extraction
│       ├── pdf_export_service.py      # reportlab PDF generation
│       ├── analytics_service.py      # Aggregation queries + benchmarks
│       └── voice_service.py          # Whisper transcription + intent parsing
├── mcp_server.py                      # Standalone MCP server wrapping all endpoints
├── chroma_db/                         # Persisted ChromaDB vector store
├── seed_demo_data.py                  # Seeds 120 synthetic claims locally
├── run_ingest.py                      # Re-ingests policy PDFs into ChromaDB
├── test_denials/                      # Sample denial PDFs for testing
├── Procfile                           # Deployment process definition
└── requirements.txt                   # All Python dependencies
```

---

## Setup & Installation

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/clairo.git
cd clairo
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the `.env` file

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free API key at [console.groq.com](https://console.groq.com)

### 5. Seed demo data

```bash
python seed_demo_data.py
```

### 6. (Optional) Re-ingest policy documents

```bash
python run_ingest.py
```

---

## Running the Server

```bash
python -m uvicorn app.main:app --reload
```

- Local: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Live: `https://web-production-ca7ed.up.railway.app`
- Live Swagger: `https://web-production-ca7ed.up.railway.app/docs`

### Running the MCP Server

In a separate terminal:

```bash
python mcp_server.py
```

To test with the MCP inspector:

```bash
npx @modelcontextprotocol/inspector python mcp_server.py
```

---

## API Endpoints — Complete Reference

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |

### Upload & Extraction

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload denial PDF — returns structured claim, classification, risk score |

### RAG Retrieval

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/rag/retrieve` | Retrieve reranked policy chunks — params: `payer`, `cpt`, `denial_reason`, `classification` |

### Appeal

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/appeal/generate-appeal` | Generate appeal using hardcoded demo claim |
| `POST` | `/appeal/generate-from-claim` | Generate appeal from real upload output |

### Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/export/viability` | Get appeal viability rating and recovery probability |
| `POST` | `/export/export-pdf` | Download formatted submission-ready appeal letter PDF |

### Risk Scoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/risk/score-claim` | Score single claim denial risk (0–100) |
| `POST` | `/risk/score-queue` | Score batch of claims sorted by risk descending |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analytics/seed` | Seed Railway database with 120 demo claims |
| `GET` | `/analytics/summary` | Practice stats with industry benchmark comparison |
| `GET` | `/analytics/by-payer` | Denial counts by payer |
| `GET` | `/analytics/by-cpt` | Denial counts by CPT code |
| `GET` | `/analytics/by-classification` | Denial type distribution with percentages |
| `GET` | `/analytics/by-month` | Month-over-month denial trend |

### Voice AI

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/voice/process` | Upload audio file — transcribes, parses intent, routes to correct endpoint, returns result + voice_response string |

### MCP Tools

| Tool | Description |
|------|-------------|
| `score_claim` | Score a claim for denial risk |
| `generate_appeal` | Generate citation-backed appeal letter |
| `retrieve_policy` | Retrieve relevant payer policy sections |
| `check_appeal_viability` | Get viability rating and recovery probability |
| `get_analytics_summary` | Get practice analytics and benchmark comparison |
| `run_full_pipeline` | Autonomously orchestrate policy retrieval + appeal generation + viability scoring in one call |

---

## Tech Stack

- **FastAPI** — REST API framework
- **Groq / LLaMA 3.3 70B** — LLM for extraction, classification, risk scoring, appeal generation, intent parsing
- **Groq Whisper Large v3** — Audio transcription for voice input
- **ChromaDB** — Local vector store for payer policy RAG
- **Sentence Transformers** (`all-MiniLM-L6-v2`) — Embeddings for semantic search
- **Custom Reranker** — Scores retrieved chunks by clinical relevance, penalizes boilerplate
- **PyMuPDF** — PDF text extraction
- **reportlab** — Formatted PDF appeal letter generation
- **MCP (Model Context Protocol)** — Agent orchestration wrapper over all CLAIRO tools
- **SQLAlchemy + SQLite** — Claim persistence and analytics
- **python-dotenv** — Environment variable management
- **Railway** — Cloud deployment

---

