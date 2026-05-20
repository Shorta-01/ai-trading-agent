"""research source prompt injection scans

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_source_prompt_injection_scans",
        sa.Column("scan_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column(
            "library_source_id",
            sa.Text(),
            sa.ForeignKey("research_sources.library_source_id"),
            nullable=False,
        ),
        sa.Column("scan_status", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.Text(), nullable=False),
        sa.Column("detected_signals_json", sa.Text(), nullable=True),
        sa.Column("safe_to_use_as_evidence", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("safe_to_use_as_instruction", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blocks_suggestions", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("research_source_prompt_injection_scans")
