"""fx rate snapshot durable storage.

Revision ID: 0026_fx_rate_snapshot_storage
Revises: 0025_ibkr_sync_snapshot_storage
Create Date: 2026-05-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0026_fx_rate_snapshot_storage"
down_revision = "0025_ibkr_sync_snapshot_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fx_rate_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("base_currency", sa.Text(), nullable=False),
        sa.Column("quote_currency", sa.Text(), nullable=False),
        sa.Column("pair", sa.Text(), nullable=False),
        sa.Column("rate", sa.Numeric(20, 6), nullable=False),
        sa.Column("rate_type", sa.Text(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("freshness_status", sa.Text(), nullable=False),
        sa.Column("validation_status", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("fx_rate_snapshots")
