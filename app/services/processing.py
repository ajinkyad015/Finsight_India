from __future__ import annotations

import tempfile
import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.chunking import chunk_pages
from app.services.pdf import ensure_pdf_magic, extract_readable_pages
from app.services.providers import EmbeddingProvider
from app.services.storage import FilingStorage


async def process_document(
    session: AsyncSession,
    storage: FilingStorage,
    embedder: EmbeddingProvider,
    document_id: uuid.UUID,
) -> None:
    document = await session.get(Document, document_id)
    if not document:
        return
    document.status = DocumentStatus.processing
    document.failure_reason = None
    await session.commit()

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            path = tmp.name
        await storage.download_to_path(document.gcs_path, path)
        ensure_pdf_magic(path)
        pages = extract_readable_pages(path)
        chunks = chunk_pages(str(document.id), pages)
        vectors = await embedder.embed([chunk.text for chunk in chunks])
        await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        for chunk, vector in zip(chunks, vectors):
            session.add(
                DocumentChunk(
                    organization_id=document.organization_id,
                    document_id=document.id,
                    chunk_id=chunk.chunk_id,
                    page_number=chunk.page_number,
                    text=chunk.text,
                    context=chunk.context,
                    embedding=vector,
                )
            )
        document.status = DocumentStatus.ready
    except Exception as exc:
        document.status = DocumentStatus.failed
        document.failure_reason = str(exc)
    await session.commit()
