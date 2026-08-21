from __future__ import annotations

import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import Principal
from app.models.document import Document, DocumentStatus
from app.schemas.documents import DocumentCreate
from app.services.pdf import validate_pdf_upload
from app.services.queue import ProcessingQueue
from app.services.storage import FilingStorage


async def create_document(
    session: AsyncSession,
    principal: Principal,
    metadata: DocumentCreate,
    file: UploadFile,
    settings: Settings,
    storage: FilingStorage,
    queue: ProcessingQueue,
) -> Document:
    data = await file.read()
    try:
        validate_pdf_upload(file.filename, file.content_type, len(data), settings.max_upload_bytes)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    document_id = uuid.uuid4()
    object_path = f"organizations/{principal.organization_id}/documents/{document_id}/{file.filename}"
    gcs_path = await storage.upload_bytes(object_path, data, file.content_type or "application/pdf")
    document = Document(
        id=document_id,
        organization_id=principal.organization_id,
        company_name=metadata.company_name,
        ticker=metadata.ticker,
        exchange=metadata.exchange,
        filing_type=metadata.filing_type,
        reporting_period=metadata.reporting_period,
        filing_date=metadata.filing_date,
        original_filename=file.filename or "upload.pdf",
        gcs_path=gcs_path,
        uploader_user_id=principal.user_id,
        status=DocumentStatus.uploaded,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    await queue.enqueue_document(str(document.id))
    return document


async def list_documents(session: AsyncSession, organization_id: str) -> list[Document]:
    result = await session.scalars(
        select(Document).where(Document.organization_id == organization_id).order_by(Document.created_at.desc())
    )
    return list(result)


async def get_document_or_404(session: AsyncSession, organization_id: str, document_id: uuid.UUID) -> Document:
    document = await session.get(Document, document_id)
    if not document or document.organization_id != organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document
