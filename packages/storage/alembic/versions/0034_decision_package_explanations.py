"""decision package AI explanations + evidence ledger.

Revision ID: 0034_decision_package_explanations
Revises: 0033_decision_package_research_evidence
Create Date: 2026-05-29
"""

import sqlalchemy as sa
from alembic import op

revision = "0034_decision_package_explanations"
down_revision = "0033_decision_package_research_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_package_explanations",
        sa.Column("explanation_id", sa.Text(), primary_key=True),
        sa.Column("decision_package_id", sa.Text(), nullable=False),
        sa.Column("decision_package_content_hash", sa.Text(), nullable=False),
        sa.Column("ibkr_conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("model_provider_code", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("input_evidence_hash", sa.Text(), nullable=False),
        sa.Column("output_text_hash", sa.Text(), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.Column("risk_disclaimer_nl", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column(
            "hallucinated_numbers_json",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "safe_for_self_learning",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "safe_for_action_drafts",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "safe_for_orders",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.UniqueConstraint(
            "decision_package_id",
            "decision_package_content_hash",
            name="uq_decision_package_explanations_pkg_hash",
        ),
    )

    op.create_table(
        "explanation_evidence_ledger",
        sa.Column("ledger_id", sa.Text(), primary_key=True),
        sa.Column("explanation_id", sa.Text(), nullable=False),
        sa.Column("evidence_kind", sa.Text(), nullable=False),
        sa.Column("evidence_reference_id", sa.Text(), nullable=False),
        sa.Column("evidence_content_hash", sa.Text(), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "safe_for_self_learning",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "safe_for_model_retraining",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_table("explanation_evidence_ledger")
    op.drop_table("decision_package_explanations")
