from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("external_id", sa.String(128), nullable=False, unique=True),
        sa.Column("name", sa.String(255)),
        sa.Column("premium_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_organizations_external_id", "organizations", ["external_id"])
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.String(128), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("ticker", sa.String(32)),
        sa.Column("exchange", sa.String(16), nullable=False),
        sa.Column("filing_type", sa.String(64), nullable=False),
        sa.Column("reporting_period", sa.String(64)),
        sa.Column("filing_date", sa.Date()),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("gcs_path", sa.String(1024), nullable=False),
        sa.Column("uploader_user_id", sa.String(128), nullable=False),
        sa.Column("status", sa.Enum("uploaded", "processing", "ready", "failed", name="documentstatus"), nullable=False),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_org_status", "documents", ["organization_id", "status"])
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.String(128), nullable=False),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", sa.String(128), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_document_chunks_tenant_doc", "document_chunks", ["organization_id", "document_id"])
    op.create_table(
        "chat_audits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.String(128), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("retrieved_chunks", sa.JSON(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "dashboard_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.String(128), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("dashboard_requests")
    op.drop_table("chat_audits")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("organizations")
    op.execute("DROP EXTENSION IF EXISTS vector")
