from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[str] = mapped_column(String(128), index=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    ticker: Mapped[str | None] = mapped_column(String(32), index=True)
    exchange: Mapped[str] = mapped_column(String(16))
    filing_type: Mapped[str] = mapped_column(String(64))
    reporting_period: Mapped[str | None] = mapped_column(String(64))
    filing_date: Mapped[date | None] = mapped_column(Date)
    original_filename: Mapped[str] = mapped_column(String(512))
    gcs_path: Mapped[str] = mapped_column(String(1024))
    uploader_user_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.uploaded, index=True)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[str] = mapped_column(String(128), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_id: Mapped[str] = mapped_column(String(128), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
