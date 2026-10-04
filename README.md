# CLΔIRO — Denial Intelligence Platform

> AI-assisted insurance denial management: upload a denial, get a risk score, payer-policy evidence, and a citation-grounded appeal letter — as a production-style full-stack system with auth, a queued AI pipeline, an audit trail, and CI/CD.

**Live demo:** [clairo-claims.vercel.app](https://clairo-claims.vercel.app) · API: [clairo-4bgp.onrender.com](https://clairo-4bgp.onrender.com) ([Swagger](https://clairo-4bgp.onrender.com/docs))

> Free-tier hosting: the API sleeps after ~15 min idle, so the first request can take 30–60 s to wake it. Sign-up takes seconds; shared demo data is visible to every account.

---

## Architecture

```
                         ┌────────────────────┐
                         │  React 19 client   │  JWT in Authorization header
                         └─────────┬──────────┘
                                   │ HTTPS
                         ┌─────────▼──────────┐
                         │   FastAPI  (REST)  │  routes → services → repositories → models
                         │  auth · RBAC · rate│  request-id · JSON logs · /metrics
                         │  limits · audit    │
                         └──┬──────┬───────┬──┘
              enqueue job   │      │       │  cache / rate-limit counters
            ┌───────────────▼┐  ┌──▼────┐ ┌▼────────────────────┐
            │   PostgreSQL    │  │Chroma │ │ Redis (optional) or │
            │ users · claims  │  │ index │ │ in-process fallback │
            │ documents ·     │  └──▲────┘ └─────────────────────┘
            │ appeals · risk  │     │ retrieval
            │ history · audit │  ┌──┴─────────────────────────────┐
            │ jobs · policies │◄─┤ Background worker (thread or    │
            └─────────────────┘  │ separate process, SKIP LOCKED)  │
                                 │ PDF → extract → classify → score│
                                 │ → RAG → appeal  (Groq LLM)      │
                                 └─────────────────────────────────┘
```

**Why a Postgres-backed queue instead of Celery/Redis?** Jobs are rows in a `jobs` table claimed with `SELECT … FOR UPDATE SKIP LOCKED`: transactional with the claim they belong to, durable across restarts, and zero extra infrastructure — which keeps the whole system deployable on free tiers. Workers run as an in-process thread by default and as a dedicated container under Docker Compose; both can run at once without double-processing. Redis is used where it earns its keep (shared cache + shared rate-limit counters) and is optional.

## What it does

| Area | Details |
|---|---|
| **Claim pipeline** | Upload a denial PDF → PyMuPDF text → LLM structured extraction → denial classification → hybrid risk score (rules 0–60 + LLM documentation review 0–40) → stored with a full score history |
| **Appeal letters** | RAG over 20+ real payer policy PDFs (ChromaDB, ONNX MiniLM embeddings, sentence-aware chunking with overlap, keyword rerank, payer-alias normalization) → grounded, citation-bearing letter with a confidence score; PDF export |
| **Prior-auth pre-check** | Per-requirement checklist against the retrieved payer policy, from clinical notes and/or uploaded documents |
| **Claims workspace** | Server-side search / filter / sort / pagination, live status while jobs run, risk breakdown + history, appeal + citations, per-claim audit timeline |
| **Policy library** | Browse indexed policies by payer; semantic search across them |
| **Analytics** | Denials by payer, CPT code, denial type and month vs industry benchmarks |
| **Voice** | Whisper transcription → intent → routed action |
| **MCP server** | 7 tools so an AI agent can run the denial→appeal workflow (see below) |
| **Admin** | Audit log of every action, `/metrics`, demo-data reseed |

## Engineering highlights

- **Auth & RBAC** — bcrypt (SHA-256 pre-hash so long passphrases stay fully significant), JWT access tokens, `user`/`admin` roles. Admins exist only via `ADMIN_EMAIL`/`ADMIN_PASSWORD` env bootstrap — self-registration can never mint one. Login failures are indistinguishable and timing-equalized (no account enumeration). Users see their own claims plus shared demo data; other tenants' claims are 404, and the LLM prompts are built only from data the caller may see.
- **PostgreSQL schema** — `users, denial_claims, documents, appeals, risk_scores, audit_logs, jobs, payer_policies` with foreign keys, composite indexes for the hot query paths, and transactional writes (claim + document + job + audit row commit together; a failed commit also removes the saved file).
- **Migrations** — Alembic, applied automatically at startup. The baseline is idempotent so it adopts the already-live `denial_claims` table without touching its rows; a test migrates a legacy-schema database and asserts rows survive, and another fails if models and migrations drift.
- **Reliability** — job retries with exponential backoff (5 s → 10 s → 20 s), permanent-vs-transient error classes, stale-job recovery if a worker dies, terminal `failed` state with a user-visible reason and a one-click re-analyze.
- **Caching** — retrieval results and per-document extraction (keyed by SHA-256, so re-uploading the same PDF skips the LLM call). Redis outage degrades to a cache miss, never an error.
- **Observability** — structured JSON logs with request IDs (also stored on audit rows), Prometheus metrics for HTTP latency/status by *route template*, LLM latency/outcome per task, job outcomes and cache hit/miss, `/health` with a DB check.
- **Safety** — per-user rate limits (per IP when anonymous, using the real client IP behind the proxy), strict upload validation (type, magic bytes, size, server-generated filenames), request-size guard, security headers, no raw vendor/model errors in user-facing fields, XSS-escaped print view.
- **Model deprecation resilience** — the LLM model id lives in one constant (`GROQ_CHAT_MODEL` overrides it). Groq retiring a model once took every AI feature down in production; the fix and the regression tests came out of a live end-to-end test pass.

### Measured: retrieval cache

`python clairo-backend/scripts/benchmark_cache.py` on the real policy index (60 distinct payer/CPT/reason lookups, in-process cache, developer laptop):

| | mean | median | p95 |
|---|---|---|---|
| cold (embed query + vector scan) | 323.5 ms | 305.2 ms | 517.1 ms |
| warm (cache hit) | 0.02 ms | 0.02 ms | 0.04 ms |

Redis adds one network round-trip per hit, so expect low single-digit milliseconds there; the benchmark uses whichever backend `REDIS_URL` selects.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, Recharts, Tailwind 4, Framer Motion |
| API | FastAPI, SQLAlchemy 2, Pydantic 2, slowapi, PyJWT, bcrypt |
| Data | PostgreSQL ([InsForge](https://insforge.dev) managed; SQLite fallback), Alembic, ChromaDB |
| AI | Groq — `openai/gpt-oss-120b` (chat), Whisper large-v3 (voice); ChromaDB's ONNX MiniLM-L6-v2 embedder (deliberately not PyTorch — see below) |
| Infra | Docker Compose, GitHub Actions, Render + Vercel |
| Quality | pytest (120 tests, run against SQLite *and* Postgres in CI), ruff, ESLint |

**Why ONNX embeddings, not sentence-transformers?** Same model, same 384-d vectors, but `sentence-transformers` drags in PyTorch (300–500 MB resident), which got the service OOM-killed on a 512 MB instance. Measured now: ~146 MB after import, ~218 MB after startup with the worker running and the embedder loaded.

## Run it

### Docker (recommended — Postgres, Redis, API, worker, frontend)

```bash
cp .env.example .env            # add GROQ_API_KEY; optionally ADMIN_EMAIL / ADMIN_PASSWORD / JWT_SECRET
docker compose up --build
```
Frontend http://localhost:5173 · API docs http://localhost:8000/docs. The API image builds the policy vector index at build time.

### Without Docker

```bash
# backend
cd clairo-backend
python -m venv venv && venv\Scripts\activate        # source venv/bin/activate on Mac/Linux
pip install -r requirements-dev.txt
cp .env.example .env                                  # GROQ_API_KEY, optional INSFORGE_DATABASE_URL (SQLite otherwise)
python run_ingest.py                                  # build the policy index (once)
uvicorn app.main:app --reload                         # migrations + worker start automatically

# frontend
cd clairo-frontend/clairo-frontend && npm install && npm run dev     # http://localhost:5173
```

InsForge Postgres (optional): `npx @insforge/cli login`, `link`, then `npx @insforge/cli db connection-string` → `INSFORGE_DATABASE_URL`.

### Tests

```bash
cd clairo-backend
pytest -q                                   # SQLite (throwaway file)
TEST_DATABASE_URL=postgresql://user:pw@localhost/clairo_test pytest -q   # real Postgres
ruff check .
```
Covered: auth & RBAC, tenant isolation, upload validation (wrong type/magic bytes/oversize/traversal filename), the full upload→analyze→appeal→audit flow, retry/backoff and permanent failure, stale-job recovery, cache TTL/eviction/Redis-outage fallback, migrations (idempotency, legacy data, model drift, downgrade), metrics label cardinality, per-user rate limiting. The LLM is always mocked, so the suite is deterministic and free.

## API

All endpoints except `/auth/*`, `/health` and `/` need `Authorization: Bearer <token>`. Interactive docs at `/docs`.

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register`, `/auth/login` | returns `{access_token, user}` |
| GET | `/auth/me` | current user |
| POST | `/claims` | multipart PDF → `202 {claim_id, job_id}`; analysis runs in the background |
| GET | `/claims` | `q, payer, classification, status, risk, sort_by, order, limit, offset` → `{items,total,…}` |
| GET | `/claims/{id}` | detail incl. risk history, appeals + citations, documents |
| POST | `/claims/{id}/analyze` · `/claims/{id}/appeal` | `202 {job_id}`; owner or admin |
| GET | `/claims/{id}/audit` | event history |
| GET | `/jobs/{id}` | `queued → running → succeeded / failed` |
| GET | `/policies` · `/policies/search?q=` | policy library / semantic search |
| GET | `/audit-logs` | admin: filter by action/user, paginated |
| GET | `/analytics/{summary,by-payer,by-cpt,by-classification,by-month}` | scoped to the caller |
| POST | `/analytics/seed` | admin JWT or `X-Admin-Key`; only touches shared demo claims |
| POST | `/risk/score-claim` · `/risk/score-queue` | stateless scoring (queue capped at 25) |
| GET | `/rag/retrieve` | stateless policy retrieval |
| POST | `/appeal/generate-from-claim` · `/export/export-pdf` · `/export/viability` | stateless helpers |
| POST | `/api/prior-auth-check` · `/api/prior-auth-check-documents` | prior-auth pre-check |
| POST | `/voice/process` | audio → intent → result |
| GET/POST | `/insforge/status`, `/live-claims`, `/agent-run` | live DB view + agent query |
| GET | `/health` · `/metrics` | `/metrics` is admin-only (JWT or `X-Admin-Key`) |

Rate limits (per user, or per IP when anonymous): 120/min default; upload, appeal and analysis 10/min; login 10/min; registration 5/min; seed 3/min; queue scoring 5/min. Exceeding returns `429` with `Retry-After`.

## MCP server

`clairo-backend/mcp_server.py` exposes 7 tools (`score_claim`, `generate_appeal`, `retrieve_policy`, `check_appeal_viability`, `get_analytics_summary`, `insforge_query`, `run_full_pipeline`) over stdio so MCP clients (Claude, Cursor, …) can drive the workflow.

```bash
cd clairo-backend
export CLAIRO_API_BASE_URL=http://127.0.0.1:8000     # default: the deployed API
export CLAIRO_API_TOKEN=<access token from POST /auth/login>   # the API requires auth
npx @modelcontextprotocol/inspector python mcp_server.py
```

## Configuration

| Variable | Where | Purpose |
|---|---|---|
| `GROQ_API_KEY` | API | LLM + Whisper (**required**) |
| `INSFORGE_DATABASE_URL` / `DATABASE_URL` | API | Postgres; SQLite file if unset |
| `JWT_SECRET` | API | token signing — **set it in production** (an ephemeral one is generated otherwise and every restart logs everyone out) |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | API | create/refresh the admin account at startup |
| `ADMIN_API_KEY` | API | optional header key for ops scripts (`/metrics`, `/analytics/seed`) |
| `REDIS_URL` | API | optional shared cache + rate limits |
| `CORS_ORIGINS` | API | extra allowed frontend origins (`*.vercel.app` etc. already allowed) |
| `GROQ_CHAT_MODEL` | API | override the chat model without a deploy |
| `WORKER_ENABLED`, `AUTO_MIGRATE`, `ALLOW_REGISTRATION`, `LOG_LEVEL`, `LOG_JSON`, `JWT_EXPIRE_MINUTES` | API | operational toggles |
| `VITE_API_URL` | frontend build | API base URL (**never put secrets in `VITE_*`** — they ship in the bundle) |

## CI/CD

`.github/workflows/ci.yml`: on every push/PR — backend lint + tests on **SQLite and a real Postgres service container**, frontend lint + build, Docker image builds and compose validation. On `main`, after everything is green, an optional **deploy** job runs when these repo secrets exist:

- `RENDER_DEPLOY_HOOK_URL` (Render → service → Settings → Deploy Hook) — triggers the API deploy, then polls `/health` until it's up
- `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` — deploys the frontend

Optional repo variable `BACKEND_URL` overrides the health-check URL.

### Deploying by hand

**Render (API):** New → Web Service → this repo, root `clairo-backend` (`render.yaml` is picked up). Set `GROQ_API_KEY`, `INSFORGE_DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`; `JWT_SECRET` is generated. Migrations run on boot.
**Vercel (frontend):** root `clairo-frontend/clairo-frontend`, `VITE_API_URL=<api url>`.

## Known limitations

- Free-tier cold starts; the in-process worker shares the web instance's CPU/RAM (move to the Compose-style dedicated worker for real load).
- Uploaded PDFs live on local disk: API and worker must share a volume (Compose does). Multi-host scaling needs object storage (S3/R2).
- Scanned/image-only PDFs aren't OCR'd — they fail with a clear message.
- Tokens are not revocable before expiry (no refresh/denylist yet); `JWT_EXPIRE_MINUTES` bounds exposure.
- Analytics' "practice denial rate" is an illustrative constant — true rates need submitted-claim volume, which isn't tracked.
- Not HIPAA-compliant: don't load real patient data without a compliance review (encryption at rest, BAAs, retention policy).

## Project structure

```
clairo-backend/
  app/
    main.py            app factory, lifespan (migrate → bootstrap admin → sync policy catalog → worker)
    config.py          typed env configuration
    models/            SQLAlchemy models (one file per table)
    schemas/           Pydantic request/response models
    repositories/      all SQL: users, claims (filters/pagination), audit, jobs (SKIP LOCKED)
    services/          claim pipeline, auth, audit, analytics, LLM services
    routes/            thin HTTP layer
    security/          hashing, JWT, auth dependencies
    jobs/              worker + handlers
    rag/               ingest, embedder, retriever, vector store
    cache.py · limiter.py · observability.py
  alembic/versions/    0001 baseline (idempotent) · 0002 production schema
  tests/               120 tests · scripts/benchmark_cache.py · mcp_server.py
clairo-frontend/clairo-frontend/src/
  auth/                AuthContext, AuthScreen
  components/          ClaimsDashboard, PolicyLibrary, AuditLogPanel, intake/appeal/prior-auth/analytics panels
.github/workflows/ci.yml · docker-compose.yml
```

## Supported payers & policies

UHC · Aetna · BCBS (TX, Arkansas, Excellus) · Cigna / ASH / eviCore · Medicare LCD · CHPW · Centene/Health Net · Molina · Kaiser · Carelon · Humana · Florida Medicaid — 20+ policy PDFs in `clairo-backend/app/data/policies/`. To add one: drop the PDF there, add a line to `run_ingest.py`, rerun it.
