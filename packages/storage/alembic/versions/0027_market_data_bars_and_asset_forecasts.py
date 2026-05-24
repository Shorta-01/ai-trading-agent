"""market-data bars and asset forecasts durable storage.

Revision ID: 0027_market_data_bars_and_asset_forecasts
Revises: 0026_fx_rate_snapshot_storage
Create Date: 2026-05-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0027_market_data_bars_and_asset_forecasts"
down_revision = "0026_fx_rate_snapshot_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_bars",
        sa.Column("bar_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("primary_exchange", sa.Text(), nullable=True),
        sa.Column("provider_code", sa.Text(), nullable=False),
        sa.Column("bar_date", sa.Date(), nullable=False),
        sa.Column("interval_code", sa.Text(), nullable=False),
        sa.Column("open_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("high_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("low_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("close_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("adjusted_close_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("volume", sa.Numeric(28, 4), nullable=True),
        sa.Column("provider_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "ibkr_conid",
            "interval_code",
            "bar_date",
            "provider_code",
            name="uq_market_data_bars_conid_interval_date_provider",
        ),
    )

    op.create_table(
        "asset_forecasts",
        sa.Column("forecast_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("model_code", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_points_used", sa.Integer(), nullable=False),
        sa.Column("history_first_bar_date", sa.Date(), nullable=True),
        sa.Column("history_last_bar_date", sa.Date(), nullable=True),
        sa.Column("current_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("expected_return_pct", sa.Numeric(20, 6), nullable=False),
        sa.Column("p10_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("p50_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("p90_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("prob_gain", sa.Numeric(10, 6), nullable=False),
        sa.Column("prob_loss", sa.Numeric(10, 6), nullable=False),
        sa.Column("prob_loss_gt_5pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("prob_loss_gt_10pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("prob_gain_gt_5pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("prob_gain_gt_10pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("expected_volatility_annual", sa.Numeric(20, 6), nullable=False),
        sa.Column("downside_risk_score", sa.Numeric(20, 6), nullable=False),
        sa.Column("confidence_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("direction_label", sa.Text(), nullable=False),
        sa.Column("direction_label_nl", sa.Text(), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column(
            "safe_for_analysis", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "safe_for_suggestions", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "safe_for_action_drafts",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_table("asset_forecasts")
    op.drop_table("market_data_bars")
