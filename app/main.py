from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import logging

from app.config import settings
from app.models.job import Job

logger = logging.getLogger(__name__)

# In-memory job store
jobs: dict[str, Job] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)
    yield

app = FastAPI(title="BIW DTM Compliance Checker API", lifespan=lifespan)

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=settings.output_dir), name="outputs")

# Imports placed after jobs definition to prevent circular imports if routers import jobs globally
from app.routers import upload, analysis, remediation

app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(remediation.router, prefix="/api/remediation", tags=["remediation"])

@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": "Resource not found"})

@app.exception_handler(500)
async def server_error_exception_handler(request: Request, exc: Exception):
    logger.error(f"Server Error: {exc}")
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": "Internal Server Error"})

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
