"""ibkr sync snapshot durable storage.

Revision ID: 0023_ibkr_sync_snapshot_storage
Revises: 0022_asset_listing_identity_foundation
Create Date: 2026-05-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0023_ibkr_sync_snapshot_storage"
down_revision = "0022_asset_listing_identity_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ibkr_sync_runs",
        sa.Column("sync_run_id", sa.Text(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_code", sa.Text(), nullable=False),
        sa.Column("provider_environment", sa.Text(), nullable=False),
        sa.Column("account_mode", sa.Text(), nullable=False),
        sa.Column("readonly", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("account_summary_status", sa.Text(), nullable=False),
        sa.Column("positions_status", sa.Text(), nullable=False),
        sa.Column("open_orders_status", sa.Text(), nullable=False),
        sa.Column("executions_status", sa.Text(), nullable=False),
        sa.Column("positions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cash_values_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("open_orders_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("executions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status_nl", sa.Text(), nullable=True),
        sa.Column("next_step_nl", sa.Text(), nullable=True),
        sa.Column("help_nl", sa.Text(), nullable=True),
        sa.Column(
            "actions_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "order_submission_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "order_modification_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "order_cancellation_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "suggestions_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ibkr_sync_runs")
