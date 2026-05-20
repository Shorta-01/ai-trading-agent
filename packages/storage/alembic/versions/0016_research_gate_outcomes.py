"""Research gate outcomes and freshness foundation.

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_gate_outcomes",
        sa.Column("gate_outcome_id", sa.Text(), nullable=False),
        sa.Column("gate_name", sa.Text(), nullable=False),
        sa.Column("gate_version", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=False),
        sa.Column("library_source_id", sa.Text(), nullable=True),
        sa.Column("evidence_item_id", sa.Text(), nullable=True),
        sa.Column("evidence_ledger_item_id", sa.Text(), nullable=True),
        sa.Column("outcome_status", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("freshness_status", sa.Text(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_age_seconds", sa.Integer(), nullable=True),
        sa.Column("blocking_reason_code", sa.Text(), nullable=True),
        sa.Column("blocks_suggestions", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.Column("source_reference_ids_json", sa.Text(), nullable=True),
        sa.Column("audit_context_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["library_source_id"], ["research_sources.library_source_id"]),
        sa.ForeignKeyConstraint(
            ["evidence_item_id"],
            ["research_source_evidence_items.evidence_item_id"],
        ),
        sa.ForeignKeyConstraint(["evidence_ledger_item_id"], ["evidence_items.evidence_id"]),
        sa.PrimaryKeyConstraint("gate_outcome_id"),
    )


def downgrade() -> None:
    op.drop_table("research_gate_outcomes")
