"""Add data-window columns to ``runtime_config``.

V1.1 Settings UI expansion (PR C): persists four API-side data-window
knobs so they're editable from the Settings page without an env-var
redeploy. Worker-side EODHD rate-limit is OUT OF SCOPE (the worker
reads its own env vars at startup; that overlay is a separate piece
of work).

Revision ID: 0059_runtime_config_data_windows
Revises: 0058_runtime_config_scheduler
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0059_runtime_config_data_windows"
down_revision = "0058_runtime_config_scheduler"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.add_column(
            sa.Column("forecast_history_lookback_days", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("forecast_minimum_bars_required", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("daily_briefing_lookback_hours", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("universe_scan_cache_ttl_hours", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("forecast_history_lookback_days")
        batch_op.drop_column("forecast_minimum_bars_required")
        batch_op.drop_column("daily_briefing_lookback_hours")
        batch_op.drop_column("universe_scan_cache_ttl_hours")
