"""asset decision packages durable storage.

Revision ID: 0029_asset_decision_packages
Revises: 0028_asset_suggestions
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0029_asset_decision_packages"
down_revision = "0028_asset_suggestions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_decision_packages",
        sa.Column("decision_package_id", sa.Text(), primary_key=True),
        sa.Column("content_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("ibkr_conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("risk_profile", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("position_snapshot_id", sa.Text(), nullable=True),
        sa.Column("position_quantity", sa.Numeric(20, 6), nullable=True),
        sa.Column("position_average_cost", sa.Numeric(20, 6), nullable=True),
        sa.Column("cash_snapshot_id", sa.Text(), nullable=True),
        sa.Column("cash_base_currency", sa.Text(), nullable=True),
        sa.Column("cash_amount", sa.Numeric(20, 6), nullable=True),
        sa.Column("market_snapshot_id", sa.Text(), nullable=True),
        sa.Column("market_last_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("market_freshness_status", sa.Text(), nullable=True),
        sa.Column("market_provider_code", sa.Text(), nullable=True),
        sa.Column("market_provider_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fx_pair", sa.Text(), nullable=True),
        sa.Column("fx_rate", sa.Numeric(20, 6), nullable=True),
        sa.Column("fx_freshness_status", sa.Text(), nullable=True),
        sa.Column("forecast_id", sa.Text(), nullable=True),
        sa.Column("forecast_model_code", sa.Text(), nullable=True),
        sa.Column("forecast_model_version", sa.Text(), nullable=True),
        sa.Column("forecast_horizon_days", sa.Integer(), nullable=True),
        sa.Column("forecast_p10_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("forecast_p50_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("forecast_p90_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("forecast_prob_gain", sa.Numeric(10, 6), nullable=True),
        sa.Column("forecast_prob_loss", sa.Numeric(10, 6), nullable=True),
        sa.Column("forecast_expected_return_pct", sa.Numeric(20, 6), nullable=True),
        sa.Column("forecast_expected_volatility_annual", sa.Numeric(20, 6), nullable=True),
        sa.Column("forecast_downside_risk_score", sa.Numeric(20, 6), nullable=True),
        sa.Column("forecast_confidence_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("suggestion_id", sa.Text(), nullable=True),
        sa.Column("suggestion_model_code", sa.Text(), nullable=True),
        sa.Column("suggestion_action_label", sa.Text(), nullable=False),
        sa.Column("suggestion_action_label_nl", sa.Text(), nullable=False),
        sa.Column("suggestion_confidence_label", sa.Text(), nullable=False),
        sa.Column("suggestion_confidence_label_nl", sa.Text(), nullable=False),
        sa.Column("suggestion_status", sa.Text(), nullable=False),
        sa.Column("has_position", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("gate_outcomes_json", sa.JSON(), nullable=True),
        sa.Column("evidence_links_json", sa.JSON(), nullable=True),
        sa.Column("audit_links_json", sa.JSON(), nullable=True),
        sa.Column("rationale_nl", sa.Text(), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
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
        sa.Column(
            "safe_for_broker_submission",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_table("asset_decision_packages")
