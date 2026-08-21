from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=4000)
    document_ids: list[uuid.UUID] | None = None
    company: str | None = Field(default=None, max_length=255)
    top_k: int = Field(default=8, ge=1, le=20)


class Citation(BaseModel):
    document_id: uuid.UUID
    page_number: int
    chunk_id: str


class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved_chunk_ids: list[str]
    unsupported: bool = False
