from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.models import DenialClaim

from app.routes.upload import router as upload_router
from app.routes.rag import router as rag_router
from app.routes.appeal import router as appeal_router
from app.routes.risk import router as risk_router
from app.routes.export import router as export_router
from app.routes.analytics import router as analytics_router
from app.routes.voice import router as voice_router
from app.routes.prior_auth import prior_auth_check_documents, router as prior_auth_router
from app.routes.insforge import router as insforge_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CLAIRO API")

# Allow requests from the Vite dev server (and any localhost port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(rag_router, prefix="/rag")
app.include_router(appeal_router, prefix="/appeal")
app.include_router(risk_router, prefix="/risk")
app.include_router(export_router, prefix="/export")
app.include_router(analytics_router, prefix="/analytics")
app.include_router(voice_router, prefix="/voice")
app.include_router(prior_auth_router, prefix="/api")

# Alias without /api prefix for clients calling /prior-auth-check-documents directly
app.post("/prior-auth-check-documents")(prior_auth_check_documents)
app.include_router(insforge_router, prefix="/insforge")

@app.get("/")
def root():
    return {"message": "CLAIRO backend is running", "db": "InsForge Postgres"}
