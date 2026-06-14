# CLAIRO Frontend

React + Vite frontend for the CLAIRO denial intelligence platform.

## Quick Start

### 1. Start the backend (in `clairo-main/`)
```bash
cd clairo-main
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Important — add CORS to the backend.**  
In `app/main.py`, add these lines right after `app = FastAPI(...)`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Start the frontend (in this folder)
```bash
npm install
npm run dev
```

Open http://localhost:5173

---

## All Backend Endpoints Used

| Feature             | Method | Path                          |
|---------------------|--------|-------------------------------|
| Upload denial PDF   | POST   | /upload                       |
| Generate appeal     | POST   | /appeal/generate-from-claim   |
| Risk score (single) | POST   | /risk/score-claim             |
| Risk score (queue)  | POST   | /risk/score-queue             |
| Policy retrieval    | GET    | /rag/retrieve                 |
| Appeal viability    | POST   | /export/viability             |
| Analytics summary   | GET    | /analytics/summary            |
| Seed demo data      | POST   | /analytics/seed               |

## Change the API URL
Edit `src/api.js` line 7:
```js
export const API_BASE_URL = "http://localhost:8000";
```

## Features
- **Upload & Extract** — Drop a denial PDF; see payer, patient ID, CPT codes, denial reason, classification, and risk score instantly.
- **Appeal Letter** — One click generates a citation-backed appeal with confidence score and viability rating.
- **Policy Citations** — Retrieves the exact payer policy sections governing the denied procedure.
- **Risk Heatmap** — Score a queue of pending claims 0–100; color-coded HIGH / MEDIUM / LOW table.
- **Analytics** — Seed demo data and view denial breakdowns by payer and category with charts.
