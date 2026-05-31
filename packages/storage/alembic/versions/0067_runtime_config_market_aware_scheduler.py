"""Add market-aware scheduler toggle columns to ``runtime_config``.

Backs the V1 market-aware scheduler (PR J): replaces the legacy
``hour="7-21"`` dumb hourly cadence with per-followed-market open /
close cron fires. Both toggles default to NULL = use the worker's
env-default (close enabled, open disabled).

Revision ID: 0067_runtime_config_market_aware_scheduler
Revises: 0066_asset_suggestions_grid_columns
Create Date: 2026-05-31
"""

import sqlalchemy as sa
from alembic import op

revision = "0067_runtime_config_market_aware_scheduler"
down_revision = "0066_asset_suggestions_grid_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.add_column(
            sa.Column(
                "scheduler_per_market_close_digest_enabled",
                sa.Boolean(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "scheduler_per_market_open_alerts_enabled",
                sa.Boolean(),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("scheduler_per_market_open_alerts_enabled")
        batch_op.drop_column("scheduler_per_market_close_digest_enabled")
