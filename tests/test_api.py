from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_chat_provider, get_embedding_provider, get_filing_storage, get_processing_queue
from app.core.config import Settings, get_settings
from app.core.security import Principal, get_current_principal
from app.db.session import Base, get_session
from app.main import app
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.providers import MockChatProvider, MockEmbeddingProvider
from app.services.queue import LocalProcessingQueue
from app.services.storage import LocalFilingStorage


@pytest.fixture
def client(tmp_path: Path):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with maker() as session:
            yield session

    def principal():
        return Principal(user_id="user-1", organization_id="org-1")

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_principal] = principal
    app.dependency_overrides[get_settings] = lambda: Settings(app_env="test", max_upload_bytes=1024 * 1024)
    app.dependency_overrides[get_filing_storage] = lambda: LocalFilingStorage(str(tmp_path))
    app.dependency_overrides[get_processing_queue] = lambda: LocalProcessingQueue()
    app.dependency_overrides[get_embedding_provider] = lambda: MockEmbeddingProvider()
    app.dependency_overrides[get_chat_provider] = lambda: MockChatProvider()
    with TestClient(app) as test_client:
        test_client.maker = maker
        yield test_client
    app.dependency_overrides.clear()


def test_upload_and_status(client):
    response = client.post(
        "/api/v1/documents",
        data={"company_name": "Acme Ltd", "exchange": "NSE", "filing_type": "annual"},
        files={"file": ("filing.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    status = client.get(f"/api/v1/documents/{document_id}")
    assert status.status_code == 200
    assert status.json()["company_name"] == "Acme Ltd"


def test_answer_endpoint(client):
    async def seed():
        async with client.maker() as session:
            doc = Document(
                organization_id="org-1",
                company_name="Acme Ltd",
                exchange="NSE",
                filing_type="annual",
                original_filename="filing.pdf",
                gcs_path="local://filing.pdf",
                uploader_user_id="user-1",
                status=DocumentStatus.ready,
            )
            session.add(doc)
            await session.flush()
            session.add(
                DocumentChunk(
                    organization_id="org-1",
                    document_id=doc.id,
                    chunk_id=f"{doc.id}:p1:c0",
                    page_number=1,
                    text="Revenue grew 10 percent year over year.",
                    context="Revenue grew 10 percent year over year.",
                    embedding=[1.0] * 16,
                )
            )
            await session.commit()

    import anyio

    anyio.run(seed)
    response = client.post("/api/v1/chat/answers", json={"question": "What happened to revenue?"})
    assert response.status_code == 200
    body = response.json()
    assert body["unsupported"] is False
    assert body["citations"][0]["page_number"] == 1
