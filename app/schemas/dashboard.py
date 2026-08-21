from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class DashboardRequestCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    document_ids: list[uuid.UUID] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list, max_length=25)


class DashboardRequestRead(BaseModel):
    id: uuid.UUID
    status: str
