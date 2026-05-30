"""Add forecast & market-behaviour columns to ``runtime_config``.

V1.1 Settings UI expansion (PR G): persists eight operator-facing
forecast + market-data toggles that were env-var-only.

Revision ID: 0063_runtime_config_forecast_market
Revises: 0062_runtime_config_sharpe_thresholds
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0063_runtime_config_forecast_market"
down_revision = "0062_runtime_config_sharpe_thresholds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.add_column(
            sa.Column("forecast_horizon_trading_days", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("forecast_ensemble_enabled", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("suggestions_risk_profile", sa.Text(), nullable=True)
        )
        batch_op.add_column(sa.Column("universe_set", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("market_data_provider", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("market_data_sync_enabled", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("ibkr_market_data_enabled", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("ibkr_market_data_type", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("ibkr_market_data_type")
        batch_op.drop_column("ibkr_market_data_enabled")
        batch_op.drop_column("market_data_sync_enabled")
        batch_op.drop_column("market_data_provider")
        batch_op.drop_column("universe_set")
        batch_op.drop_column("suggestions_risk_profile")
        batch_op.drop_column("forecast_ensemble_enabled")
        batch_op.drop_column("forecast_horizon_trading_days")
