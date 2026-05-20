"""research source evidence items

Revision ID: 0014_research_source_evidence_items
Revises: 0013_research_source_credibility_assessments
Create Date: 2026-05-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0014_research_source_evidence_items"
down_revision = "0013_research_source_credibility_assessments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_source_evidence_items",
        sa.Column("evidence_item_id", sa.Text(), nullable=False),
        sa.Column("library_source_id", sa.Text(), nullable=False),
        sa.Column("evidence_type", sa.Text(), nullable=False),
        sa.Column("evidence_status", sa.Text(), nullable=False),
        sa.Column("extracted_from_kind", sa.Text(), nullable=False),
        sa.Column("source_reference_text", sa.Text(), nullable=False),
        sa.Column("normalized_evidence_text", sa.Text(), nullable=False),
        sa.Column("evidence_summary_nl", sa.Text(), nullable=False),
        sa.Column("asset_symbol", sa.Text(), nullable=True),
        sa.Column("reporting_period", sa.Text(), nullable=True),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("confidence_level", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.Text(), nullable=False),
        sa.Column("source_text_hash_sha256", sa.Text(), nullable=True),
        sa.Column("extraction_run_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "safe_to_use_as_evidence", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column(
            "safe_to_use_for_suggestions",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("blocks_suggestions", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["library_source_id"], ["research_sources.library_source_id"]),
        sa.PrimaryKeyConstraint("evidence_item_id"),
    )


def downgrade() -> None:
    op.drop_table("research_source_evidence_items")
