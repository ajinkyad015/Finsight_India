from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_chat_provider, get_embedding_provider, get_filing_storage, get_processing_queue
from app.core.config import Settings, get_settings
from app.core.security import Principal, get_current_principal
from app.db.session import get_session
from app.schemas.chat import AnswerRequest, AnswerResponse
from app.schemas.dashboard import DashboardRequestCreate, DashboardRequestRead
from app.schemas.documents import DocumentCreate, DocumentRead
from app.services.answers import answer_question
from app.services.dashboard import create_dashboard_request
from app.services.documents import create_document, get_document_or_404, list_documents
from app.services.providers import ChatProvider, EmbeddingProvider
from app.services.queue import ProcessingQueue
from app.services.storage import FilingStorage

router = APIRouter(prefix="/api/v1")


@router.post("/documents", response_model=DocumentRead, status_code=201)
async def upload_document(
    company_name: str = Form(...),
    exchange: str = Form(...),
    filing_type: str = Form(...),
    ticker: str | None = Form(default=None),
    reporting_period: str | None = Form(default=None),
    filing_date: str | None = Form(default=None),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
    storage: FilingStorage = Depends(get_filing_storage),
    queue: ProcessingQueue = Depends(get_processing_queue),
):
    metadata = DocumentCreate(
        company_name=company_name,
        ticker=ticker,
        exchange=exchange,
        filing_type=filing_type,
        reporting_period=reporting_period,
        filing_date=filing_date,
    )
    return await create_document(session, principal, metadata, file, settings, storage, queue)


@router.get("/documents", response_model=list[DocumentRead])
async def documents(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    return await list_documents(session, principal.organization_id)


@router.get("/documents/{document_id}", response_model=DocumentRead)
async def document_status(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    return await get_document_or_404(session, principal.organization_id, document_id)


@router.post("/chat/answers", response_model=AnswerResponse)
async def chat_answer(
    request: AnswerRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
    chat: ChatProvider = Depends(get_chat_provider),
):
    return await answer_question(session, principal, request, embedder, chat)


@router.post("/dashboard/requests", response_model=DashboardRequestRead, status_code=201)
async def dashboard_request(
    request: DashboardRequestCreate,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    return await create_dashboard_request(session, principal, request)


health = APIRouter()


@health.get("/health")
async def healthcheck():
    return {"status": "ok"}


@health.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)):
    await session.execute(text("select 1"))
    return {"status": "ready"}
