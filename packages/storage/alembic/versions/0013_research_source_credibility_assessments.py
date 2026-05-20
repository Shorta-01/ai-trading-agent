"""research source credibility assessments

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_source_credibility_assessments",
        sa.Column("assessment_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column(
            "library_source_id",
            sa.Text(),
            sa.ForeignKey("research_sources.library_source_id"),
            nullable=False,
        ),
        sa.Column("credibility_status", sa.Text(), nullable=False),
        sa.Column("credibility_level", sa.Text(), nullable=False),
        sa.Column("source_category", sa.Text(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence_level", sa.Text(), nullable=False),
        sa.Column("credibility_signals_json", sa.Text(), nullable=True),
        sa.Column("limitation_notes_nl", sa.Text(), nullable=True),
        sa.Column(
            "safe_to_use_as_evidence",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "safe_to_use_for_suggestions",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("blocks_suggestions", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("research_source_credibility_assessments")
