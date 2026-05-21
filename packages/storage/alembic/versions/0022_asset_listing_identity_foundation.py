"""asset listing identity foundation

Revision ID: 0022_asset_listing_identity_foundation
Revises: 0021_market_data_storage_foundation
Create Date: 2026-05-21
"""

import sqlalchemy as sa
from alembic import op

revision = "0022_asset_listing_identity_foundation"
down_revision = "0021_market_data_storage_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_listings",
        sa.Column("listing_id", sa.Text(), nullable=False),
        sa.Column("asset_id", sa.Text(), nullable=False),
        sa.Column("ibkr_conid", sa.Text(), nullable=True),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("local_symbol", sa.Text(), nullable=True),
        sa.Column("trading_class", sa.Text(), nullable=True),
        sa.Column("security_type", sa.Text(), nullable=False),
        sa.Column("asset_class", sa.Text(), nullable=True),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("primary_exchange", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("listing_country", sa.Text(), nullable=True),
        sa.Column("listing_status", sa.Text(), nullable=False),
        sa.Column("validation_status", sa.Text(), nullable=False),
        sa.Column("validation_source", sa.Text(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("identity_confidence", sa.Text(), nullable=False),
        sa.Column("identity_source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_reference_ids_json", sa.JSON(), nullable=True),
        sa.Column("audit_context_json", sa.JSON(), nullable=True),
        sa.Column(
            "safe_to_use_for_market_data", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column(
            "safe_to_use_for_analysis", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column(
            "safe_to_use_for_suggestions", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("blocks_market_data", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("blocks_analysis", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("blocks_suggestions", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["asset_master_records.asset_id"]),
        sa.PrimaryKeyConstraint("listing_id"),
    )


def downgrade() -> None:
    op.drop_table("asset_listings")
