"""scheduler runs audit table.

Revision ID: 0037_scheduler_runs
Revises: 0036_daily_briefings
Create Date: 2026-06-01
"""

import sqlalchemy as sa
from alembic import op

revision = "0037_scheduler_runs"
down_revision = "0036_daily_briefings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduler_runs",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("job_name", sa.Text(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.Text(), nullable=False),
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
    op.drop_table("scheduler_runs")
