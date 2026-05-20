"""Research extracted text metadata storage foundation.

Revision ID: 0011_research_extracted_text
Revises: 0010_research_source_archive
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_research_extracted_text"
down_revision = "0010_research_source_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_extracted_texts",
        sa.Column("extracted_text_id", sa.Text(), nullable=False),
        sa.Column("library_source_id", sa.Text(), nullable=False),
        sa.Column("source_file_hash_sha256", sa.Text(), nullable=True),
        sa.Column("extraction_status", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.Text(), nullable=False),
        sa.Column("detected_content_type", sa.Text(), nullable=True),
        sa.Column("detected_language", sa.Text(), nullable=True),
        sa.Column("character_count", sa.Integer(), nullable=True),
        sa.Column("line_count", sa.Integer(), nullable=True),
        sa.Column("text_hash_sha256", sa.Text(), nullable=True),
        sa.Column("extracted_text_storage_uri", sa.Text(), nullable=True),
        sa.Column("preview_text_nl", sa.Text(), nullable=True),
        sa.Column(
            "can_be_used_in_research", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "can_be_used_in_suggestions",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("needs_user_review", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("blocks_suggestions", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("reason_nl", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["library_source_id"], ["research_sources.library_source_id"]),
        sa.PrimaryKeyConstraint("extracted_text_id"),
    )


def downgrade() -> None:
    op.drop_table("research_extracted_texts")
