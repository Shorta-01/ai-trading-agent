"""universe scan runs audit table.

Revision ID: 0039_universe_scan_runs
Revises: 0038_asset_fundamentals_snapshots
Create Date: 2026-06-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0039_universe_scan_runs"
down_revision = "0038_asset_fundamentals_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "universe_scan_runs",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("triggered_by", sa.Text(), nullable=False),
        sa.Column("scanned_count", sa.Integer(), nullable=False),
        sa.Column("persisted_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("ranked_count", sa.Integer(), nullable=False),
        sa.Column("universe_size", sa.Integer(), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
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
    )


def downgrade() -> None:
    op.drop_table("universe_scan_runs")
