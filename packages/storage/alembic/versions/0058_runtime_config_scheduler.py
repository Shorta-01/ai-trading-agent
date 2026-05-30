"""Add scheduler-cadence columns to ``runtime_config``.

V1.1 Settings UI expansion (PR B): persists the operator's
daily-briefing cron and IBKR-sync interval so they're editable from
the Settings page without an env-var redeploy. Worker-side sweep
settings (interval, retry, alert threshold) are NOT yet exposed —
the worker reads its own env vars at startup and doesn't query
``runtime_config``; that overlay is a separate piece of work.

Revision ID: 0058_runtime_config_scheduler
Revises: 0057_runtime_config_order_policy
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0058_runtime_config_scheduler"
down_revision = "0057_runtime_config_order_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.add_column(
            sa.Column("scheduler_daily_briefing_cron", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("ibkr_sync_interval_minutes", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("scheduler_daily_briefing_cron")
        batch_op.drop_column("ibkr_sync_interval_minutes")
