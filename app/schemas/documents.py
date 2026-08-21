from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus


class DocumentCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    ticker: str | None = Field(default=None, max_length=32)
    exchange: str = Field(..., pattern="^(NSE|BSE)$")
    filing_type: str = Field(..., min_length=1, max_length=64)
    reporting_period: str | None = Field(default=None, max_length=64)
    filing_date: date | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    ticker: str | None
    exchange: str
    filing_type: str
    reporting_period: str | None
    filing_date: date | None
    original_filename: str
    status: DocumentStatus
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
