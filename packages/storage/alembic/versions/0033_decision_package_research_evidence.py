"""decision package research evidence columns.

Revision ID: 0033_decision_package_research_evidence
Revises: 0032_prediction_diary_entries
Create Date: 2026-05-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0033_decision_package_research_evidence"
down_revision = "0032_prediction_diary_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "asset_decision_packages",
        sa.Column(
            "research_evidence_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "asset_decision_packages",
        sa.Column("research_credibility_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "asset_decision_packages",
        sa.Column("research_freshness_status", sa.Text(), nullable=True),
    )
    op.add_column(
        "asset_decision_packages",
        sa.Column("research_blocking_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "asset_decision_packages",
        sa.Column("research_snippet_nl", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("asset_decision_packages", "research_snippet_nl")
    op.drop_column("asset_decision_packages", "research_blocking_reason")
    op.drop_column("asset_decision_packages", "research_freshness_status")
    op.drop_column("asset_decision_packages", "research_credibility_summary")
    op.drop_column("asset_decision_packages", "research_evidence_count")
