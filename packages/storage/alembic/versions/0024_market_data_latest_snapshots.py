"""Task 119A phase 1: latest market-data snapshot storage.

Revision ID: 0024_market_data_latest_snapshots
Revises: 0023_request_log_provider_freshness_contracts
Create Date: 2026-05-21
"""
import sqlalchemy as sa
from alembic import op

revision = "0024_market_data_latest_snapshots"
down_revision = "0023_request_log_provider_freshness_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_latest_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("asset_class", sa.Text(), nullable=True),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("primary_exchange", sa.Text(), nullable=True),
        sa.Column("provider_code", sa.Text(), nullable=True),
        sa.Column("provider_environment", sa.Text(), nullable=True),
        sa.Column("provider_account_mode", sa.Text(), nullable=True),
        sa.Column("market_data_type", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("bid_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("ask_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("close_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("day_change_percent", sa.Numeric(18, 6), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("freshness_status", sa.Text(), nullable=True),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.Column("request_log_id", sa.Text(), nullable=True),
        sa.Column("provider_source_id", sa.Text(), nullable=True),
        sa.Column("freshness_audit_id", sa.Text(), nullable=True),
        sa.Column("safe_for_analysis", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("safe_for_suggestions", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "safe_for_action_drafts",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ibkr_conid <> ''",
            name="ck_market_data_latest_snapshots_ibkr_conid_not_empty",
        ),
    )


def downgrade() -> None:
    op.drop_table("market_data_latest_snapshots")
