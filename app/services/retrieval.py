from __future__ import annotations

import math
import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.providers import EmbeddingProvider


def cosine_similarity(left: list[float], right: list[float]) -> float:
    denom = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(x * x for x in right))
    if denom == 0:
        return 0
    return sum(x * y for x, y in zip(left, right)) / denom


async def retrieve_chunks(
    session: AsyncSession,
    embedder: EmbeddingProvider,
    organization_id: str,
    question: str,
    document_ids: list[uuid.UUID] | None,
    company: str | None,
    top_k: int,
) -> list[dict]:
    query_vector = (await embedder.embed([question]))[0]
    stmt: Select = (
        select(DocumentChunk, Document)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.organization_id == organization_id)
        .where(Document.organization_id == organization_id)
        .where(Document.status == DocumentStatus.ready)
    )
    if document_ids:
        stmt = stmt.where(Document.id.in_(document_ids))
    if company:
        stmt = stmt.where(Document.company_name.ilike(f"%{company}%"))

    rows = (await session.execute(stmt)).all()
    ranked = []
    for chunk, document in rows:
        if not chunk.embedding:
            continue
        ranked.append(
            (
                cosine_similarity(query_vector, chunk.embedding),
                {
                    "document_id": str(document.id),
                    "company_name": document.company_name,
                    "ticker": document.ticker,
                    "filing_type": document.filing_type,
                    "filing_date": document.filing_date.isoformat() if document.filing_date else None,
                    "page_number": chunk.page_number,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "context": chunk.context,
                },
            )
        )
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:top_k]]
