# CLAIRO — Denial Intelligence Platform

## Overview

CLAIRO is a full-stack AI-powered insurance denial management platform. It parses denial PDFs, classifies denials, scores claim risk, retrieves payer policy citations via RAG, and generates formal appeal letters using Groq LLMs.

---

## Tech Stack

**Backend:** FastAPI, SQLAlchemy (SQLite), ChromaDB, Groq (LLaMA 3.3 70B), Sentence Transformers, PyMuPDF, ReportLab

**Frontend:** React 19, Vite, Recharts, Tailwind-compatible CSS

---

## Project Structure

```
clairo-main/
├── clairo-backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS middleware
│   │   ├── database.py          # SQLite engine + session
│   │   ├── models.py            # DenialClaim ORM model
│   │   ├── routes/              # upload, appeal, risk, rag, export, analytics, voice
│   │   ├── services/            # LLM services (Groq), PDF, risk scoring, analytics
│   │   └── rag/                 # Embedder, vector store (ChromaDB), retriever, ingest
│   ├── app/data/policies/       # Pre-loaded payer policy PDFs
│   ├── requirements.txt
│   └── .env                     # You create this (see setup)
└── clairo-frontend/
    └── clairo-frontend/
        └── src/
            ├── App.jsx
            ├── api.js           # All backend API calls
            └── components/      # UploadPanel, ClaimDetails, AppealPanel, PolicyPanel, RiskHeatmap, AnalyticsPanel
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

Start the server:
```bash
uvicorn app.main:app --reload
```

Backend runs at **http://localhost:8000**

### Frontend

```bash
cd clairo-main/clairo-frontend/clairo-frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

---

## Features

### Upload & Extract
Upload any insurance denial PDF. CLAIRO extracts payer, patient ID, CPT codes, denial reason, billed/denied amounts, and service date using LLM parsing.

### Claim Details
Displays all extracted fields alongside the denial classification (e.g. `medical_necessity`, `prior_authorization`) and a 0–100 risk score with risk level badge.

### Appeal Letter Generator
Generates a formal, citation-backed appeal letter grounded in retrieved payer policy evidence. Returns a confidence score, rationale, viability rating, and recovery probability estimate.

### Policy Citation Retrieval
Retrieves the most relevant policy chunks from the ChromaDB vector store for the claim's payer and CPT code combination, using enriched semantic queries and keyword reranking.

### Denial Risk Heatmap
Scores a queue of claims 0–100 for denial probability using a hybrid rule-based + LLM documentation analysis engine. Flags prior auth requirements, bundling risks, and documentation gaps.

### Analytics Dashboard
Practice-level denial analytics including total denials, appeals generated, average risk score, denied revenue estimate, and denial rate vs. industry benchmark. Includes bar charts by payer and denial category.

---

## Seeding Demo Data

On first run, go to the **Analytics** tab and click **Seed Demo Data**. This inserts 120 synthetic denial claims across 5 payers and 6 denial categories.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload denial PDF, extract + classify + score |
| POST | `/appeal/generate-from-claim` | Generate appeal letter from structured claim |
| POST | `/export/viability` | Get appeal viability rating |
| POST | `/export/export-pdf` | Export appeal letter as PDF |
| GET | `/rag/retrieve` | Retrieve policy citations |
| POST | `/risk/score-claim` | Score a single claim |
| POST | `/risk/score-queue` | Score a batch of claims |
| GET | `/analytics/summary` | Practice-level summary stats |
| GET | `/analytics/by-payer` | Denial counts by payer |
| GET | `/analytics/by-classification` | Denial counts by category |
| GET | `/analytics/by-month` | Denial trend by month |
| POST | `/analytics/seed` | Seed demo data |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Required. Your Groq API key for LLM and Whisper calls |
| `CHROMA_PATH` | Optional. Path to ChromaDB storage (default: `chroma_db`) |

---

## Notes

- The ChromaDB vector store is pre-populated with policy PDFs from `app/data/policies/`. To re-ingest, run `python run_ingest.py` from `clairo-backend/`.
- All LLM calls use `llama-3.3-70b-versatile` via Groq. Voice transcription uses `whisper-large-v3`.
- The SQLite database (`clairo.db`) is auto-created on first startup.
