# CLΔIRO — Denial Intelligence Platform

> AI-powered insurance denial management, built on InsForge's agent-native cloud database.

CLAIRO is a full-stack AI platform that helps healthcare providers fight insurance denials. It parses denial PDFs, classifies denials, scores claim risk, runs prior authorization pre-checks against real payer policies, generates citation-backed appeal letters via Groq LLMs, and exposes every tool via an MCP server so AI agents can autonomously orchestrate the full denial-to-appeal pipeline.

**InsForge is CLAIRO's persistent memory.** Every denial processed, every risk score computed, and every appeal generated is stored in InsForge Postgres — giving CLAIRO agents real historical context before they act, and giving the practice a live, queryable record of their entire denial history.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Database** | **InsForge** (managed Postgres) — agent-native, MCP-accessible |
| **Backend** | FastAPI + SQLAlchemy + ChromaDB |
| **LLM / Voice** | Groq — LLaMA 3.3 70B + Whisper Large v3 |
| **Vector Search** | Sentence Transformers + ChromaDB (20+ real payer PDFs) |
| **MCP Server** | 7 tools including `insforge_query` for live DB access |
| **Frontend** | React 19 + Vite + Recharts |

---

## How InsForge Fits

```
   Denial PDF Upload
         │
         ▼
   CLAIRO FastAPI ──── InsForge Postgres ◄──── AI Agent (MCP)
         │                    │                      │
    Risk Scoring         Stores every           insforge_query tool
    RAG Retrieval        claim + result         reads live DB context
    Appeal Gen                                  before acting
         │
         ▼
   InsForge DB updated ──► Live Feed shown in InsForge tab
```

CLAIRO's MCP server exposes an `insforge_query` tool that lets any MCP-compatible agent (Claude, Cursor, Copilot) query the InsForge Postgres database directly for live claim context before running risk scoring or appeal generation. This is the "agentic loop" — InsForge is not just storage, it's the agent's memory.

---

## Features

### 1. Upload & Extract
Upload any insurance denial PDF. CLAIRO extracts payer, patient ID, CPT codes, denial reason, billed/denied amounts, and service date using Groq LLM, then classifies the denial and scores its risk. Every result is stored in InsForge Postgres.

### 2. Denial Risk Scoring
Hybrid rule-based + LLM documentation analysis. Flags prior auth requirements, bundling risks, and documentation gaps. Returns a 0–100 risk score with specific remediation recommendations.

### 3. Appeal Letter Generator
Generates a formal, citation-backed appeal letter grounded in retrieved payer policy evidence. Returns appeal strength rating (Strong/Moderate/Weak), confidence score, and industry context from AHA 2023 data. Export as PDF.

### 4. Prior Authorization Pre-Check
Per-requirement policy checklist before filing a PA request. Retrieves the real payer policy from ChromaDB and evaluates each criterion against the clinical notes. Returns `pa_required`, gap flags, urgency level, and a single actionable recommendation.

### 5. Policy Citation Retrieval
Semantic search over 20+ real payer policy PDFs (Aetna, UHC, BCBS, Cigna, Medicare, and more). Payer-specific policies receive a relevance bonus and results are keyword-reranked for clinical criteria sections.

### 6. InsForge Live Database
A dedicated tab showing the live InsForge Postgres backend — real-time claim feed, aggregate stats (total claims, high-risk count, appeal rate), and an autonomous agent query interface that reads from InsForge before synthesizing denial intelligence.

### 7. Analytics Dashboard
Practice-level analytics: denials by payer, by category, by CPT code, and by month. Includes industry benchmark comparison. Payer name normalization merges variants (UHC / UnitedHealthCare / UNITEDHEALTHCARE).

### 8. Voice AI
Record or upload an audio file. Groq Whisper Large v3 transcribes it, LLM parses the intent, and CLAIRO routes to the right endpoint — returning both a structured result and a plain-English voice response.

### 9. MCP Server
7 tools for autonomous agent orchestration: `score_claim`, `generate_appeal`, `retrieve_policy`, `check_appeal_viability`, `get_analytics_summary`, `run_full_pipeline`, and `insforge_query`.

---

## Setup & Running

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | Backend |
| Node.js 18+ | Frontend |
| [Groq API key](https://console.groq.com) | Free — LLM + Whisper |
| [InsForge account](https://insforge.dev) | Free — Postgres database |

---

### Step 1 — InsForge Database Setup

CLAIRO uses [InsForge](https://insforge.dev) as its agent-native cloud database. Sign up free at insforge.dev, then:

```bash
# Install and authenticate the InsForge CLI (always via npx)
npx @insforge/cli login

# From the repo root, link this directory to your InsForge project
npx @insforge/cli link

# Verify
npx @insforge/cli current
```

Apply the CLAIRO schema migration:

```bash
npx @insforge/cli db migrations up --all
# This runs: migrations/001_create_denial_claims.sql
```

Get your connection string:

```bash
npx @insforge/cli db connection-string
# Copy the output — paste it into .env as INSFORGE_DATABASE_URL
```

> **No InsForge account?** The backend automatically falls back to a local SQLite file (`clairo.db`). All features work. The InsForge tab will show a "local fallback" banner instead of cloud stats.

---

### Step 2 — Backend

```bash
cd clairo-backend
python -m venv venv

# Activate
source venv/bin/activate     # Mac/Linux
venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

Create `.env` in `clairo-backend/` (copy from `.env.example`):

```bash
cp .env.example .env
```

Then fill in:

```env
GROQ_API_KEY=your_groq_api_key_here
INSFORGE_DATABASE_URL=postgresql://...   # from: npx @insforge/cli db connection-string
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

- API: **http://localhost:8000**
- Swagger: **http://localhost:8000/docs**

---

### Step 3 — Frontend

```bash
cd clairo-frontend/clairo-frontend
npm install
npm run dev
```

Frontend: **http://localhost:5173**

---

### Step 4 — Seed Demo Data (optional)

Go to the **Analytics** tab → click **Seed Demo Data**. This inserts 120 synthetic denial claims into InsForge Postgres and populates all charts. The **InsForge** tab will immediately show a live feed of those claims.

---

### Step 5 — MCP Server (optional, for agent use)

```bash
cd clairo-backend
python mcp_server.py

# Test with the MCP inspector (run from inside clairo-backend so the
# filename resolves correctly — no path prefix needed):
npx @modelcontextprotocol/inspector python mcp_server.py
```

> **Note:** Run the inspector command from inside `clairo-backend`. If you pass a
> path like `clairo-backend/mcp_server.py` from a different working directory, some
> shells/inspector versions mis-join it (e.g. `clairo-backendmcp_server.py`) and
> you'll get a "can't open file" error.

The MCP server exposes 7 tools including `insforge_query`, which lets any MCP-compatible AI agent (Claude, Cursor, Copilot) query the InsForge database directly before running denial analysis.

By default the server talks to the deployed CLAIRO API. To point it at your local
backend instead (e.g. `http://127.0.0.1:8000`, useful for routes like `/insforge/*`
that may not exist on every deployment), set:

```bash
# Mac/Linux
export CLAIRO_API_BASE_URL=http://127.0.0.1:8000

# Windows (PowerShell)
$env:CLAIRO_API_BASE_URL = "http://127.0.0.1:8000"
```

All tool calls now return structured `{"error": "..."}` JSON instead of crashing
the MCP connection if the backend is unreachable or returns an unexpected response.

---

### Docker (optional)

```bash
# From the repo root
cp clairo-backend/.env.example clairo-backend/.env  # fill in keys
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000

---

## Project Structure

```
clairo/                                  # repo root
├── docker-compose.yml
├── migrations/
│   └── 001_create_denial_claims.sql    # InsForge DB migration
├── clairo-backend/
│   ├── .env.example
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── mcp_server.py                   # MCP server — 7 tools incl. insforge_query
│   ├── app/
│   │   ├── database.py                 # InsForge Postgres (SQLite fallback)
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── routes/
│   │   │   ├── insforge.py             # /insforge/status, /live-claims, /agent-run
│   │   │   ├── upload.py
│   │   │   ├── appeal.py
│   │   │   ├── prior_auth.py
│   │   │   ├── risk.py
│   │   │   ├── export.py
│   │   │   ├── rag.py
│   │   │   ├── analytics.py
│   │   │   └── voice.py
│   │   ├── services/
│   │   ├── rag/
│   │   └── data/policies/              # 20+ real payer policy PDFs
│   └── chroma_db/                      # Pre-populated vector store
└── clairo-frontend/
    └── clairo-frontend/
        ├── Dockerfile
        └── src/
            ├── components/
            │   ├── InsforgePanel.jsx   # Live DB feed + agent query UI
            │   ├── AnalyticsPanel.jsx
            │   ├── AppealPanel.jsx
            │   ├── PriorAuthPanel.jsx
            │   ├── RiskHeatmap.jsx
            │   ├── VoiceAIPanel.jsx
            │   └── ...
            └── api.js
```

---

## InsForge Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/insforge/status` | DB health check + live stats (total claims, high risk, appeal rate) |
| GET | `/insforge/live-claims` | Latest N claims from InsForge Postgres, newest first |
| POST | `/insforge/agent-run` | Autonomous agent: queries InsForge DB then synthesizes denial intelligence |

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `insforge_query` | **Query InsForge Postgres** for live claim stats and history. Gives agents historical context before acting. |
| `score_claim` | Score a claim for denial risk (0–100) |
| `generate_appeal` | Generate citation-backed appeal letter |
| `retrieve_policy` | Retrieve payer policy sections via semantic search |
| `check_appeal_viability` | Get appeal strength rating |
| `get_analytics_summary` | Practice analytics + industry benchmark |
| `run_full_pipeline` | Autonomous end-to-end denial-to-appeal pipeline |

---

## API Endpoints

### Upload & Extraction
| POST | `/upload` | Upload denial PDF → structured claim + classification + risk score |

### Appeal
| POST | `/appeal/generate-from-claim` | Generate appeal from upload output |
| POST | `/appeal/generate-appeal` | Demo appeal (hardcoded claim) |

### Prior Authorization
| POST | `/api/prior-auth-check` | PA pre-submission gap analysis |

### Risk
| POST | `/risk/score-claim` | Score single claim (0–100) |
| POST | `/risk/score-queue` | Score batch of claims, sorted by risk |

### Export
| POST | `/export/export-pdf` | Download formatted appeal letter as PDF |
| POST | `/export/viability` | Appeal strength rating |

### RAG
| GET | `/rag/retrieve` | Retrieve reranked policy chunks |

### Analytics
| POST | `/analytics/seed` | Seed 120 demo claims (add `?force=true` to reseed) |
| GET | `/analytics/summary` | Practice stats + benchmark |
| GET | `/analytics/by-payer` | Denials by payer |
| GET | `/analytics/by-cpt` | Denials by CPT code |
| GET | `/analytics/by-classification` | Denial type distribution |
| GET | `/analytics/by-month` | Monthly trend |

### Voice
| POST | `/voice/process` | Audio file → transcription → intent → routed result |

---

## Supported Payers & Policies

| Payer | Policy |
|-------|--------|
| UHC | Knee arthroscopy, spine surgery, MSK imaging |
| Aetna | Medical necessity, MSK policy |
| BCBS TX | Orthopedic surgical policy |
| BCBS Arkansas | Meniscal transplantation |
| Cigna | Electric stimulation clinical guidelines + cardiac imaging |
| Medicare | LCD for knee arthroscopy (CMS.gov) |
| CHPW | Knee arthroscopy and arthroplasty |
| Centene/Health Net | Articular cartilage defect repairs |
| Excellus BCBS | Autologous chondrocyte implantation |

Adding a policy: drop the PDF in `app/data/policies/`, add one line to `run_ingest.py`, run `python run_ingest.py`.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | **Yes** | Groq API key for LLM and Whisper |
| `INSFORGE_DATABASE_URL` | Recommended | InsForge Postgres connection string. Falls back to SQLite if unset. |
| `CHROMA_PATH` | No | ChromaDB storage path (default: `chroma_db`) |

---

## Demo Script (for the video)

1. **Open CLAIRO** → watch the shader intro → enter the app
2. **InsForge tab** → show the live DB status banner (InsForge Postgres, Xms latency), stats cards, live claim feed
3. **Run an agent query** → "What are the highest-risk claims?" → watch it pull from InsForge and synthesize
4. **CLΔIRO tab** → upload a denial PDF → extraction + classification + risk score appear
5. **InsForge tab** → refresh → the new claim appears in the live feed instantly
6. **Appeal Letter tab** → generate appeal → download PDF
7. **Prior Authorization tab** → paste clinical notes → show the per-requirement checklist
8. **Analytics tab** → show the four charts, industry benchmark comparison
9. **MCP Inspector** → show `insforge_query` tool call returning live DB data
