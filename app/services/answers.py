from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal
from app.models.audit import ChatAudit
from app.schemas.chat import AnswerRequest, AnswerResponse
from app.services.citations import validate_model_response
from app.services.providers import ChatProvider, EmbeddingProvider
from app.services.retrieval import retrieve_chunks


async def answer_question(
    session: AsyncSession,
    principal: Principal,
    request: AnswerRequest,
    embedder: EmbeddingProvider,
    chat: ChatProvider,
) -> AnswerResponse:
    retrieved = await retrieve_chunks(
        session=session,
        embedder=embedder,
        organization_id=principal.organization_id,
        question=request.question,
        document_ids=request.document_ids,
        company=request.company,
        top_k=request.top_k,
    )
    model_response = await chat.answer_json(request.question, retrieved)
    validated = validate_model_response(model_response, retrieved)
    audit = ChatAudit(
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        question=request.question,
        answer=validated["answer"],
        retrieved_chunks=retrieved,
        citations=validated["citations"],
    )
    session.add(audit)
    await session.commit()
    return AnswerResponse(
        answer=validated["answer"],
        citations=validated["citations"],
        retrieved_chunk_ids=[chunk["chunk_id"] for chunk in retrieved],
        unsupported=validated["unsupported"],
    )
