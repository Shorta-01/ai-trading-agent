"""asset_action_drafts Belgian TOB columns.

Revision ID: 0035_action_draft_belgian_tob
Revises: 0034_decision_package_explanations
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0035_action_draft_belgian_tob"
down_revision = "0034_decision_package_explanations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "asset_action_drafts",
        sa.Column("estimated_belgian_tob", sa.Numeric(20, 6), nullable=True),
    )
    op.add_column(
        "asset_action_drafts",
        sa.Column("belgian_tob_security_class", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("asset_action_drafts", "belgian_tob_security_class")
    op.drop_column("asset_action_drafts", "estimated_belgian_tob")
