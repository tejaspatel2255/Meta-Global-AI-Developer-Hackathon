"""FastAPI application — Phase 0: health and models probe only."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from benchguard import __version__
from benchguard.contracts.http import HealthResponse, ModelsResponse

app = FastAPI(title="BenchGuard", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@app.get("/api/models", response_model=ModelsResponse)
@app.get("/models", response_model=ModelsResponse)
def models() -> ModelsResponse:
    """Report whether a key is configured. Do not call Meta from this probe."""
    has_key = bool(os.environ.get("MODEL_API_KEY", "").strip())
    return ModelsResponse(sam=has_key, spark=has_key)
