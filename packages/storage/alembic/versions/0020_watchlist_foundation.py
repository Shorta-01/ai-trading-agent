"""watchlist foundation

Revision ID: 0020_watchlist_foundation
Revises: 0019_source_to_asset_linking_foundation
Create Date: 2026-05-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0020_watchlist_foundation"
down_revision = "0019_source_to_asset_linking_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("watchlist_item_id", sa.Text(), nullable=False),
        sa.Column("asset_id", sa.Text(), nullable=True),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("security_type", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("symbol <> ''", name="ck_watchlist_items_symbol_not_empty"),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_watchlist_items_status_valid",
        ),
        sa.CheckConstraint("source = 'manual'", name="ck_watchlist_items_source_manual"),
        sa.ForeignKeyConstraint(["asset_id"], ["asset_master_records.asset_id"]),
        sa.PrimaryKeyConstraint("watchlist_item_id"),
    )
    op.create_index(
        "ix_watchlist_items_active_symbol_exchange_currency",
        "watchlist_items",
        ["symbol", "exchange", "currency"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_watchlist_items_active_symbol_exchange_currency",
        table_name="watchlist_items",
    )
    op.drop_table("watchlist_items")
