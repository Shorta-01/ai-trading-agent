"""asset suggestions durable storage.

Revision ID: 0028_asset_suggestions
Revises: 0027_market_data_bars_and_asset_forecasts
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0028_asset_suggestions"
down_revision = "0027_market_data_bars_and_asset_forecasts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_suggestions",
        sa.Column("suggestion_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("forecast_id", sa.Text(), nullable=True),
        sa.Column("model_code", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_profile", sa.Text(), nullable=False),
        sa.Column("has_position", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("action_label", sa.Text(), nullable=False),
        sa.Column("action_label_nl", sa.Text(), nullable=False),
        sa.Column("confidence_label", sa.Text(), nullable=False),
        sa.Column("confidence_label_nl", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("rationale_nl", sa.Text(), nullable=False),
        sa.Column("drivers_json", sa.JSON(), nullable=True),
        sa.Column("blockers_json", sa.JSON(), nullable=True),
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
    op.drop_table("asset_suggestions")
