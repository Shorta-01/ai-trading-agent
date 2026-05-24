"""asset action drafts durable storage.

Revision ID: 0030_asset_action_drafts
Revises: 0029_asset_decision_packages
Create Date: 2026-05-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0030_asset_action_drafts"
down_revision = "0029_asset_decision_packages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_action_drafts",
        sa.Column("draft_id", sa.Text(), primary_key=True),
        sa.Column("decision_package_id", sa.Text(), nullable=False),
        sa.Column("decision_package_content_hash", sa.Text(), nullable=False),
        sa.Column("ibkr_conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("primary_exchange", sa.Text(), nullable=True),
        sa.Column("account_mode", sa.Text(), nullable=False),
        sa.Column("expected_account_mode", sa.Text(), nullable=False),
        sa.Column("action_side", sa.Text(), nullable=False),
        sa.Column("order_type", sa.Text(), nullable=False),
        sa.Column("tif", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("limit_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("estimated_order_value", sa.Numeric(20, 6), nullable=True),
        sa.Column("estimated_cash_before", sa.Numeric(20, 6), nullable=True),
        sa.Column("estimated_cash_after", sa.Numeric(20, 6), nullable=True),
        sa.Column("estimated_position_quantity_before", sa.Numeric(20, 6), nullable=True),
        sa.Column("estimated_position_quantity_after", sa.Numeric(20, 6), nullable=True),
        sa.Column("estimated_position_value_after", sa.Numeric(20, 6), nullable=True),
        sa.Column("estimated_portfolio_weight_after_pct", sa.Numeric(10, 6), nullable=True),
        sa.Column("estimated_concentration_impact_pct", sa.Numeric(10, 6), nullable=True),
        sa.Column("orderimpact_base_currency", sa.Text(), nullable=True),
        sa.Column("source_action_label", sa.Text(), nullable=False),
        sa.Column("source_action_label_nl", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("dry_run_status", sa.Text(), nullable=False),
        sa.Column("dry_run_failures_json", sa.JSON(), nullable=True),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column("rationale_nl", sa.Text(), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "safe_for_submission",
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
    op.drop_table("asset_action_drafts")
