from __future__ import annotations

import uuid

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_embedding_provider, get_filing_storage
from app.db.session import get_session
from app.services.processing import process_document
from app.services.providers import EmbeddingProvider
from app.services.storage import FilingStorage

app = FastAPI(title="NSE/BSE Filing RAG Worker", version="0.1.0")


class ProcessRequest(BaseModel):
    document_id: uuid.UUID


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/worker/process")
async def process(
    request: ProcessRequest,
    session: AsyncSession = Depends(get_session),
    storage: FilingStorage = Depends(get_filing_storage),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
):
    await process_document(session, storage, embedder, request.document_id)
    return {"status": "accepted", "document_id": str(request.document_id)}
