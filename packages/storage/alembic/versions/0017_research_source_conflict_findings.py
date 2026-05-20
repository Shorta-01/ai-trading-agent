"""Add research source conflict findings foundation.

Revision ID: 0017_research_source_conflict_findings
Revises: 0016_research_gate_outcomes
Create Date: 2026-05-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0017_research_source_conflict_findings"
down_revision = "0016_research_gate_outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_source_conflict_findings",
        sa.Column("conflict_finding_id", sa.Text(), nullable=False),
        sa.Column("conflict_status", sa.Text(), nullable=False),
        sa.Column("conflict_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("primary_source_id", sa.Text(), nullable=False),
        sa.Column("conflicting_source_id", sa.Text(), nullable=True),
        sa.Column("primary_evidence_item_id", sa.Text(), nullable=True),
        sa.Column("conflicting_evidence_item_id", sa.Text(), nullable=True),
        sa.Column("primary_evidence_ledger_item_id", sa.Text(), nullable=True),
        sa.Column("conflicting_evidence_ledger_item_id", sa.Text(), nullable=True),
        sa.Column("gate_outcome_id", sa.Text(), nullable=True),
        sa.Column("asset_symbol", sa.Text(), nullable=True),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("reporting_period", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("conflict_summary_nl", sa.Text(), nullable=False),
        sa.Column("conflict_reason_nl", sa.Text(), nullable=False),
        sa.Column("source_reference_ids_json", sa.Text(), nullable=True),
        sa.Column("audit_context_json", sa.Text(), nullable=True),
        sa.Column(
            "safe_to_use_as_evidence", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "safe_to_use_for_suggestions",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "blocks_suggestions", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["primary_source_id"], ["research_sources.library_source_id"]),
        sa.ForeignKeyConstraint(["conflicting_source_id"], ["research_sources.library_source_id"]),
        sa.ForeignKeyConstraint(
            ["primary_evidence_item_id"], ["research_source_evidence_items.evidence_item_id"]
        ),
        sa.ForeignKeyConstraint(
            ["conflicting_evidence_item_id"], ["research_source_evidence_items.evidence_item_id"]
        ),
        sa.ForeignKeyConstraint(
            ["primary_evidence_ledger_item_id"], ["evidence_items.evidence_id"]
        ),
        sa.ForeignKeyConstraint(
            ["conflicting_evidence_ledger_item_id"], ["evidence_items.evidence_id"]
        ),
        sa.ForeignKeyConstraint(["gate_outcome_id"], ["research_gate_outcomes.gate_outcome_id"]),
        sa.PrimaryKeyConstraint("conflict_finding_id"),
    )


def downgrade() -> None:
    op.drop_table("research_source_conflict_findings")
