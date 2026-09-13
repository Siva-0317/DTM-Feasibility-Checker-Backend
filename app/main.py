from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.config import settings
from app.routers import upload, analysis, remediation
from app.models.job import Job

# In-memory job store
jobs: dict[str, Job] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event that creates uploads/ and outputs/ dirs if they don't exist
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)
    yield
    # Shutdown logic if any

app = FastAPI(title="BIW DTM Compliance Checker API", lifespan=lifespan)

# CORS middleware allowing CORS_ORIGINS from config
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(remediation.router, prefix="/api/remediation", tags=["remediation"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
