
# CLAIRO — Denial Intelligence Platform

## Overview

CLAIRO is a full-stack AI-powered insurance denial management platform. It parses denial PDFs, classifies denials, scores claim risk, runs prior authorization pre-checks against payer policy, retrieves payer policy citations via RAG, generates formal appeal letters using Groq LLMs, supports voice-commanded workflows, and exposes all tools via an MCP server for autonomous agent orchestration.

We currently support 10+ payer policies across orthopedics, cardiology, behavioral health, and Medicare — with a clear pipeline to 200+ policies at production scale.

---

## Tech Stack

**Backend:** FastAPI, SQLAlchemy (SQLite), ChromaDB, Groq (LLaMA 3.3 70B + Whisper Large v3), Sentence Transformers, PyMuPDF, ReportLab

**Frontend:** React 19, Vite, Recharts, Tailwind-compatible CSS

---

## Project Structure

```
clairo-main/
├── clairo-backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app + CORS middleware
│   │   ├── database.py                # SQLite engine + session
│   │   ├── models.py                  # DenialClaim ORM model
│   │   ├── schemas.py
│   │   ├── routes/
│   │   │   ├── upload.py              # POST /upload
│   │   │   ├── appeal.py              # POST /appeal/generate-appeal, /appeal/generate-from-claim
│   │   │   ├── prior_auth.py          # POST /api/prior-auth-check
│   │   │   ├── risk.py                # POST /risk/score-claim, /risk/score-queue
│   │   │   ├── export.py              # POST /export/export-pdf, /export/viability
│   │   │   ├── rag.py                 # GET /rag/retrieve
│   │   │   ├── analytics.py           # GET /analytics/*, POST /analytics/seed
│   │   │   └── voice.py               # POST /voice/process
│   │   ├── services/
│   │   │   ├── groq_services.py       # Groq client initialization
│   │   │   ├── extraction_service.py  # Structured claim extraction
│   │   │   ├── classification_service.py  # Denial classification
│   │   │   ├── appeal_service.py      # Appeal generation + appeal strength scoring
│   │   │   ├── risk_service.py        # Hybrid risk scoring engine
│   │   │   ├── pdf_service.py         # PyMuPDF text extraction
│   │   │   ├── pdf_export_service.py  # ReportLab PDF generation
│   │   │   ├── analytics_service.py   # Aggregation queries + benchmarks
│   │   │   └── voice_service.py       # Whisper transcription + intent parsing
│   │   ├── rag/
│   │   │   ├── embedder.py            # Lazy-loaded sentence-transformers model
│   │   │   ├── ingest.py              # Loads policy PDFs into ChromaDB
│   │   │   ├── loader.py              # PDF text chunking
│   │   │   ├── retriever.py           # Semantic search + custom reranker
│   │   │   └── vectorstore.py         # ChromaDB persistent client
│   │   ├── data/policies/             # Pre-loaded payer policy PDFs
│   │   └── uploads/                   # Uploaded denial letter PDFs
│   ├── mcp_server.py                  # Standalone MCP server wrapping all endpoints
│   ├── chroma_db/                     # Persisted ChromaDB vector store
│   ├── seed_demo_data.py              # Seeds 120 synthetic claims
│   ├── run_ingest.py                  # Re-ingests policy PDFs into ChromaDB
│   ├── test_denials/                  # Sample denial text files for testing
│   ├── Procfile
│   ├── render.yaml
│   └── requirements.txt
└── clairo-frontend/
    └── clairo-frontend/
        └── src/
            ├── App.jsx
            ├── api.js                 # All backend API calls
            └── components/
                ├── UploadPanel.jsx
                ├── ClaimDetails.jsx
                ├── AppealPanel.jsx
                ├── PolicyPanel.jsx
                ├── PriorAuthPanel.jsx
                ├── RiskHeatmap.jsx
                ├── AnalyticsPanel.jsx
                ├── VoicePanel.jsx
                └── ui.jsx
```

---

## Setup & Running

### Prerequisites
- Python 3.10+
- Node.js 18+
- A free [Groq API key](https://console.groq.com)

### Backend

```bash
cd clairo-main/clairo-backend
python -m venv venv

# Activate
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

Create a `.env` file in `clairo-backend/`:
```
GROQ_API_KEY=your_groq_api_key_here
```

Optionally re-ingest the policy PDFs into ChromaDB (already pre-populated, only needed if you add new policy documents):
```bash
python run_ingest.py
```

Start the server:
```bash
uvicorn app.main:app --reload
```

Backend runs at **http://localhost:8000**  
Swagger UI at **http://localhost:8000/docs**

### Frontend

```bash
cd clairo-main/clairo-frontend/clairo-frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

---

## Features

### 1. Upload & Extract
Upload any insurance denial PDF. CLAIRO extracts payer, patient ID, CPT codes, denial reason, billed/denied amounts, and service date using LLM parsing, then immediately classifies the denial and scores its risk.

### 2. Claim Details
Displays all extracted fields alongside the denial classification (e.g. `medical_necessity`, `prior_authorization`) and a 0–100 risk score with risk level badge.

### 3. Appeal Letter Generator
Generates a formal, citation-backed appeal letter grounded in retrieved payer policy evidence. Returns an appeal strength rating (Strong / Moderate / Weak), a 0–100 strength score, a plain-English rationale citing how many payer-required criteria are met, and industry context grounded in AHA 2023 appeal overturn data. The letter can be copied to clipboard or exported as a formatted, submission-ready PDF.

### 4. Prior Authorization Pre-Check
Submit clinical notes, CPT codes, diagnosis codes, and payer before filing a prior authorization request. CLAIRO retrieves the relevant payer policy from ChromaDB, compares the submitted documentation against policy requirements, and returns three structured lists — what documentation is present, what is missing, and a single actionable recommendation for what to fix or gather before submitting the PA. Covers UHC, Aetna, Cigna, Medicare, BCBS, and more.

### 5. PDF Export
Downloads the generated appeal letter as a formatted PDF including a claim header (payer, patient ID, CPT codes, service date, denied amount) and an AI-assisted disclaimer. Requires an appeal letter to be generated first.

### 6. Policy Citation Retrieval
Retrieves the most relevant policy chunks from the ChromaDB vector store for the claim's payer and CPT code combination, using enriched semantic queries and keyword reranking that prioritizes clinical criteria sections over boilerplate.

### 7. Denial Risk Heatmap
Scores a queue of claims 0–100 for denial probability using a hybrid rule-based + LLM documentation analysis engine. Flags prior auth requirements, bundling risks, and documentation gaps. Supports both demo queue scoring and single-claim scoring from a real upload.

### 8. Analytics Dashboard
Practice-level denial analytics including total denials, appeals generated, average risk score, denied revenue estimate, and denial rate vs. industry benchmark. Includes four charts: denials by payer, denials by category, monthly denial trend, and denials by CPT code.

### 9. Voice AI
Accepts an audio file upload, transcribes it via Groq Whisper Large v3, extracts intent and claim fields using LLM parsing, and automatically routes to the correct backend endpoint. Supports `score_claim` and `check_analytics` intents, returning both a structured result and a plain-English voice response string.

### 10. MCP Server
A standalone Model Context Protocol server that exposes all CLAIRO tools so AI agents can autonomously orchestrate the complete denial-to-appeal pipeline without a human in the loop.

---

## Supported Payers & Policies

CLAIRO currently has 10+ payer policies ingested across four clinical domains:

| Payer | Policy Coverage |
|-------|----------------|
| UHC | Knee arthroscopy clinical policy + behavioral health |
| Aetna | MSK policy + general medical necessity criteria |
| BCBS TX | Orthopedic surgical policy |
| BCBS Arkansas | Meniscal transplantation |
| Cigna | Electric stimulation clinical guidelines + cardiac imaging |
| Humana | MSK coverage |
| CHPW | Knee arthroscopy and arthroplasty |
| Centene / Health Net | Articular cartilage defect repairs |
| Excellus BCBS | Autologous chondrocyte implantation |
| Medicare | LCD for knee arthroscopy (CMS.gov) |

Adding a new policy takes under 5 minutes: drop the PDF in `app/data/policies/`, add one line to `run_ingest.py`, and run it.

---

## Seeding Demo Data

On first run, go to the **Analytics** tab and click **Seed Demo Data**. This inserts 120 synthetic denial claims across 5 payers and 6 denial categories so all four charts populate with meaningful data.

---

## API Endpoints

### Core
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |

### Upload & Extraction
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload denial PDF — returns structured claim, classification, risk score |

### Appeal
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/appeal/generate-appeal` | Generate appeal using hardcoded demo claim |
| POST | `/appeal/generate-from-claim` | Generate appeal from real upload output |

### Prior Authorization
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/prior-auth-check` | Compare clinical notes against payer PA policy — returns present/missing documentation and recommendation |

**Request body:**
```json
{
  "payer": "UHC",
  "cpt_codes": ["29881"],
  "clinical_notes": "Patient presented with knee pain...",
  "diagnosis_codes": ["M23.201"]
}
```

**Response:**
```json
{
  "payer": "UHC",
  "cpt_code": "29881",
  "policy_requirements": ["..."],
  "documentation_present": ["..."],
  "documentation_missing": ["..."],
  "recommendation": "Submit conservative therapy records (6+ weeks) and MRI findings before submitting PA",
  "policy_source": "UHC Knee Arthroscopy Clinical Policy, Section 3.2"
}
```

### Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/export/viability` | Get appeal strength rating and industry context |
| POST | `/export/export-pdf` | Download formatted submission-ready appeal letter PDF |

### RAG Retrieval
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/rag/retrieve` | Retrieve reranked policy chunks — params: `payer`, `cpt`, `denial_reason`, `classification` |

### Risk Scoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/risk/score-claim` | Score single claim denial risk (0–100) |
| POST | `/risk/score-queue` | Score batch of claims sorted by risk descending |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analytics/seed` | Seed database with 120 demo claims |
| GET | `/analytics/summary` | Practice stats with industry benchmark comparison |
| GET | `/analytics/by-payer` | Denial counts by payer |
| GET | `/analytics/by-cpt` | Denial counts by CPT code |
| GET | `/analytics/by-classification` | Denial type distribution with percentages |
| GET | `/analytics/by-month` | Month-over-month denial trend |

### Voice AI
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/voice/process` | Upload audio file — transcribes, parses intent, routes to correct endpoint, returns result + voice_response string |

### MCP Tools
| Tool | Description |
|------|-------------|
| `score_claim` | Score a claim for denial risk |
| `generate_appeal` | Generate citation-backed appeal letter |
| `retrieve_policy` | Retrieve relevant payer policy sections |
| `check_appeal_viability` | Get appeal strength rating and industry context |
| `get_analytics_summary` | Get practice analytics and benchmark comparison |
| `run_full_pipeline` | Autonomously orchestrate policy retrieval + appeal generation + viability scoring in one call |

---

## Appeal Strength Scoring

Appeal responses no longer return a raw recovery probability. Instead they return a defensible, citation-backed strength assessment:

```json
{
  "appeal_strength": "Strong",
  "appeal_strength_score": 84,
  "appeal_strength_rationale": "4 of 5 payer-required criteria are directly addressed by submitted documentation. Policy citations are applicable and denial reason is addressable on appeal.",
  "industry_context": "Appeals with direct policy citations overturn at 60-67% vs 39% industry average (AHA 2023)"
}
```

Strength levels: **Strong** (score ≥ 70) · **Moderate** (45–69) · **Weak** (< 45). Scores are adjusted for payer strictness (UHC, Cigna, Anthem penalized –10) and denial category (medical necessity, documentation gap, and coding mismatch rewarded +5; timely filing and eligibility penalized –15).

---

## Running the MCP Server

In a separate terminal:

```bash
cd clairo-main/clairo-backend
python mcp_server.py
```

To test with the MCP inspector:

```bash
npx @modelcontextprotocol/inspector python mcp_server.py
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Required. Your Groq API key for LLM and Whisper calls |
| `CHROMA_PATH` | Optional. Path to ChromaDB storage (default: `chroma_db`) |

---

## Notes

- The ChromaDB vector store is pre-populated with policy PDFs from `app/data/policies/`. To add new policies, drop the PDF in that folder, add one line to `run_ingest.py`, and run `python run_ingest.py` from `clairo-backend/`.
- All LLM calls use `llama-3.3-70b-versatile` via Groq. Voice transcription uses `whisper-large-v3`.
- The SQLite database (`clairo.db`) is auto-created on first startup.
- Every real denial upload automatically feeds the analytics dashboard.
- The PDF export endpoint requires `appeal_letter`, `structured_claim`, `confidence_score`, and `classification` in the request body.
- The `/api/prior-auth-check` endpoint is designed to be called before a PA submission, not after a denial — it is a pre-submission gap analysis tool, not an appeal tool.
