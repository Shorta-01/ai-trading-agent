"""market data storage foundation

Revision ID: 0021_market_data_storage_foundation
Revises: 0020_watchlist_foundation
Create Date: 2026-05-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0021_market_data_storage_foundation"
down_revision = "0020_watchlist_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_snapshots",
        sa.Column("snapshot_id", sa.Text(), nullable=False),
        sa.Column("watchlist_item_id", sa.Text(), nullable=False),
        sa.Column("asset_id", sa.Text(), nullable=True),
        sa.Column("ibkr_conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("security_type", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("primary_exchange", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("provider_name", sa.Text(), nullable=False),
        sa.Column("data_kind", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("freshness_status", sa.Text(), nullable=False),
        sa.Column("validation_status", sa.Text(), nullable=False),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("raw_reference", sa.Text(), nullable=True),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "ibkr_conid <> ''",
            name="ck_market_data_snapshots_ibkr_conid_not_empty",
        ),
        sa.CheckConstraint("symbol <> ''", name="ck_market_data_snapshots_symbol_not_empty"),
        sa.CheckConstraint(
            "provider_name <> ''",
            name="ck_market_data_snapshots_provider_name_not_empty",
        ),
        sa.CheckConstraint("data_kind <> ''", name="ck_market_data_snapshots_data_kind_not_empty"),
        sa.ForeignKeyConstraint(["watchlist_item_id"], ["watchlist_items.watchlist_item_id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["asset_master_records.asset_id"]),
        sa.PrimaryKeyConstraint("snapshot_id"),
    )


def downgrade() -> None:
    op.drop_table("market_data_snapshots")
