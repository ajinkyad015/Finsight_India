from __future__ import annotations

import uuid

import pytest

from app.core.security import Principal
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.chunking import chunk_pages
from app.services.citations import UNSUPPORTED, validate_model_response
from app.services.dashboard import create_dashboard_request
from app.services.pdf import validate_pdf_upload
from app.services.retrieval import retrieve_chunks


class StaticEmbedder:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] if "revenue" in text.lower() else [0.0, 1.0] for text in texts]


def test_pdf_validation_rejects_non_pdf():
    with pytest.raises(ValueError):
        validate_pdf_upload("filing.txt", "text/plain", 12, 100)


def test_chunk_metadata_preserves_page_and_context():
    chunks = chunk_pages("doc-1", [(7, "alpha " * 1000)], size=100, overlap=10)
    assert chunks[0].chunk_id == "doc-1:p7:c0"
    assert chunks[0].page_number == 7
    assert "alpha" in chunks[0].context


def test_citation_validation_removes_invalid_citations():
    doc_id = uuid.uuid4()
    result = validate_model_response(
        {"answer": "Revenue increased.", "citations": [{"chunk_id": "missing"}]},
        [{"chunk_id": "valid", "document_id": str(doc_id), "page_number": 3, "text": "Revenue increased."}],
    )
    assert result["unsupported"] is True
    assert result["answer"] == UNSUPPORTED


@pytest.mark.asyncio
async def test_retrieval_filters_by_tenant_and_ready_status(db_session):
    ready = Document(
        organization_id="org-a",
        company_name="Acme",
        exchange="NSE",
        filing_type="annual",
        original_filename="a.pdf",
        gcs_path="local://a.pdf",
        uploader_user_id="u",
        status=DocumentStatus.ready,
    )
    other_org = Document(
        organization_id="org-b",
        company_name="Acme",
        exchange="NSE",
        filing_type="annual",
        original_filename="b.pdf",
        gcs_path="local://b.pdf",
        uploader_user_id="u",
        status=DocumentStatus.ready,
    )
    failed = Document(
        organization_id="org-a",
        company_name="Acme",
        exchange="NSE",
        filing_type="annual",
        original_filename="c.pdf",
        gcs_path="local://c.pdf",
        uploader_user_id="u",
        status=DocumentStatus.failed,
    )
    db_session.add_all([ready, other_org, failed])
    await db_session.flush()
    db_session.add_all(
        [
            DocumentChunk(
                organization_id="org-a",
                document_id=ready.id,
                chunk_id="ready",
                page_number=1,
                text="revenue grew",
                context="revenue grew",
                embedding=[1.0, 0.0],
            ),
            DocumentChunk(
                organization_id="org-b",
                document_id=other_org.id,
                chunk_id="other",
                page_number=1,
                text="revenue grew",
                context="revenue grew",
                embedding=[1.0, 0.0],
            ),
            DocumentChunk(
                organization_id="org-a",
                document_id=failed.id,
                chunk_id="failed",
                page_number=1,
                text="revenue grew",
                context="revenue grew",
                embedding=[1.0, 0.0],
            ),
        ]
    )
    await db_session.commit()

    chunks = await retrieve_chunks(db_session, StaticEmbedder(), "org-a", "revenue", None, None, 5)
    assert [chunk["chunk_id"] for chunk in chunks] == ["ready"]


@pytest.mark.asyncio
async def test_premium_gating_rejects_missing_premium(db_session):
    principal = Principal(user_id="u", organization_id="org-free")
    from app.schemas.dashboard import DashboardRequestCreate

    with pytest.raises(Exception) as exc:
        await create_dashboard_request(db_session, principal, DashboardRequestCreate(title="Board pack"))
    assert getattr(exc.value, "status_code") == 403
