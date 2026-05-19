"""Research source archive storage foundation."""

import sqlalchemy as sa
from alembic import op

revision = "0010_research_source_archive"
down_revision = "0009_evidence_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_sources",
        sa.Column("library_source_id", sa.Text(), primary_key=True),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("classification_status", sa.Text(), nullable=False),
        sa.Column("extraction_status", sa.Text(), nullable=False),
        sa.Column("analysis_status", sa.Text(), nullable=False),
        sa.Column("asset_symbol", sa.Text(), nullable=True),
        sa.Column("asset_name", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("document_type", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_credibility_level", sa.Text(), nullable=True),
        sa.Column("prompt_injection_risk_level", sa.Text(), nullable=True),
        sa.Column("content_hash_sha256", sa.Text(), nullable=True),
        sa.Column("archive_storage_uri", sa.Text(), nullable=True),
        sa.Column("raw_source_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
    )

    op.create_table(
        "research_uploaded_file_metadata",
        sa.Column(
            "library_source_id",
            sa.Text(),
            sa.ForeignKey("research_sources.library_source_id"),
            primary_key=True,
        ),
        sa.Column("original_file_name", sa.Text(), nullable=False),
        sa.Column("stored_file_name", sa.Text(), nullable=True),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("file_hash_sha256", sa.Text(), nullable=True),
        sa.Column("detected_language", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_by_user", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
    )

    op.create_table(
        "research_url_metadata",
        sa.Column(
            "library_source_id",
            sa.Text(),
            sa.ForeignKey("research_sources.library_source_id"),
            primary_key=True,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=True),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_hash_sha256", sa.Text(), nullable=True),
        sa.Column("snapshot_storage_uri", sa.Text(), nullable=True),
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("user_supplied", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
    )

    op.create_table(
        "research_user_notes",
        sa.Column(
            "library_source_id",
            sa.Text(),
            sa.ForeignKey("research_sources.library_source_id"),
            primary_key=True,
        ),
        sa.Column("asset_symbol", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("note_nl", sa.Text(), nullable=False),
        sa.Column("thesis_relevance_nl", sa.Text(), nullable=True),
        sa.Column("user_confidence_nl", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
    )

    op.create_table(
        "research_document_sets",
        sa.Column("document_set_id", sa.Text(), primary_key=True),
        sa.Column("asset_symbol", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("set_type", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
    )

    op.create_table(
        "research_document_set_members",
        sa.Column("member_id", sa.Text(), primary_key=True),
        sa.Column(
            "document_set_id",
            sa.Text(),
            sa.ForeignKey("research_document_sets.document_set_id"),
            nullable=False,
        ),
        sa.Column(
            "library_source_id",
            sa.Text(),
            sa.ForeignKey("research_sources.library_source_id"),
            nullable=False,
        ),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("reporting_period", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "research_document_classifications",
        sa.Column("classification_id", sa.Text(), primary_key=True),
        sa.Column(
            "library_source_id",
            sa.Text(),
            sa.ForeignKey("research_sources.library_source_id"),
            nullable=False,
        ),
        sa.Column("document_type", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Text(), nullable=False),
        sa.Column("detected_asset_symbol", sa.Text(), nullable=True),
        sa.Column("detected_asset_name", sa.Text(), nullable=True),
        sa.Column("detected_fiscal_year", sa.Integer(), nullable=True),
        sa.Column("detected_reporting_period", sa.Text(), nullable=True),
        sa.Column("detected_language", sa.Text(), nullable=True),
        sa.Column("needs_user_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason_nl", sa.Text(), nullable=False),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
    )

    op.create_table(
        "research_source_asset_links",
        sa.Column("link_id", sa.Text(), primary_key=True),
        sa.Column(
            "library_source_id",
            sa.Text(),
            sa.ForeignKey("research_sources.library_source_id"),
            nullable=False,
        ),
        sa.Column("asset_symbol", sa.Text(), nullable=True),
        sa.Column("asset_name", sa.Text(), nullable=True),
        sa.Column("conid", sa.Text(), nullable=True),
        sa.Column("isin", sa.Text(), nullable=True),
        sa.Column("link_type", sa.Text(), nullable=False),
        sa.Column("mapping_confidence", sa.Text(), nullable=False),
        sa.Column("auto_linked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "requires_user_confirmation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("confirmed_by_user", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason_nl", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "research_source_processing_status",
        sa.Column("processing_id", sa.Text(), primary_key=True),
        sa.Column(
            "library_source_id",
            sa.Text(),
            sa.ForeignKey("research_sources.library_source_id"),
            nullable=False,
        ),
        sa.Column("classification_status", sa.Text(), nullable=False),
        sa.Column("extraction_status", sa.Text(), nullable=False),
        sa.Column("analysis_status", sa.Text(), nullable=False),
        sa.Column("readiness_status", sa.Text(), nullable=False),
        sa.Column(
            "can_be_used_in_research",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "can_be_used_in_suggestions",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("needs_user_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blocks_suggestions", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_error_nl", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason_nl", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("research_source_processing_status")
    op.drop_table("research_source_asset_links")
    op.drop_table("research_document_classifications")
    op.drop_table("research_document_set_members")
    op.drop_table("research_document_sets")
    op.drop_table("research_user_notes")
    op.drop_table("research_url_metadata")
    op.drop_table("research_uploaded_file_metadata")
    op.drop_table("research_sources")
