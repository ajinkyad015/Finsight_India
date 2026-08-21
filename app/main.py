from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, router
from app.core.logging import RequestIdMiddleware, configure_logging

configure_logging()

app = FastAPI(title="NSE/BSE Filing RAG Service", version="0.1.0")
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["authorization", "content-type", "x-request-id", "x-dev-user-id", "x-dev-organization-id"],
)
app.include_router(health)
app.include_router(router)
