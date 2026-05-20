"""research source evidence ledger links

Revision ID: 0015_research_source_evidence_ledger_links
Revises: 0014_research_source_evidence_items
Create Date: 2026-05-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0015_research_source_evidence_ledger_links"
down_revision = "0014_research_source_evidence_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_source_evidence_ledger_links",
        sa.Column("link_id", sa.Text(), nullable=False),
        sa.Column("library_source_id", sa.Text(), nullable=False),
        sa.Column("evidence_item_id", sa.Text(), nullable=False),
        sa.Column("evidence_ledger_item_id", sa.Text(), nullable=False),
        sa.Column("link_type", sa.Text(), nullable=False),
        sa.Column("link_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_system", sa.Text(), nullable=False),
        sa.Column("lineage_scope", sa.Text(), nullable=False),
        sa.Column("source_snapshot_reference", sa.Text(), nullable=True),
        sa.Column("evidence_text_hash_sha256", sa.Text(), nullable=True),
        sa.Column("gate_context_status", sa.Text(), nullable=False),
        sa.Column(
            "safe_to_use_for_suggestions",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("blocks_suggestions", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["library_source_id"], ["research_sources.library_source_id"]),
        sa.ForeignKeyConstraint(
            ["evidence_item_id"], ["research_source_evidence_items.evidence_item_id"]
        ),
        sa.ForeignKeyConstraint(["evidence_ledger_item_id"], ["evidence_items.evidence_id"]),
        sa.PrimaryKeyConstraint("link_id"),
    )


def downgrade() -> None:
    op.drop_table("research_source_evidence_ledger_links")
