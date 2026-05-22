"""ibkr sync snapshot durable storage.

Revision ID: 0025_ibkr_sync_snapshot_storage
Revises: 0024_market_data_latest_snapshots
Create Date: 2026-05-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0025_ibkr_sync_snapshot_storage"
down_revision = "0024_market_data_latest_snapshots"
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

    op.create_table(
        "ibkr_account_cash_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column(
            "sync_run_id",
            sa.Text(),
            sa.ForeignKey("ibkr_sync_runs.sync_run_id"),
            nullable=False,
        ),
        sa.Column("account_ref", sa.Text(), nullable=True),
        sa.Column("base_currency", sa.Text(), nullable=False),
        sa.Column("cash", sa.Numeric(18, 6), nullable=True),
        sa.Column("available_funds", sa.Numeric(18, 6), nullable=True),
        sa.Column("buying_power", sa.Numeric(18, 6), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "ibkr_position_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column(
            "sync_run_id",
            sa.Text(),
            sa.ForeignKey("ibkr_sync_runs.sync_run_id"),
            nullable=False,
        ),
        sa.Column("account_ref", sa.Text(), nullable=True),
        sa.Column("conid", sa.Text(), nullable=True),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("security_type", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("primary_exchange", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("average_cost", sa.Numeric(18, 6), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "ibkr_open_order_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column(
            "sync_run_id",
            sa.Text(),
            sa.ForeignKey("ibkr_sync_runs.sync_run_id"),
            nullable=False,
        ),
        sa.Column("account_ref", sa.Text(), nullable=True),
        sa.Column("ibkr_order_id", sa.Integer(), nullable=False),
        sa.Column("ibkr_perm_id", sa.Integer(), nullable=True),
        sa.Column("parent_order_id", sa.Integer(), nullable=True),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("security_type", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("primary_exchange", sa.Text(), nullable=True),
        sa.Column("action_side", sa.Text(), nullable=False),
        sa.Column("order_type", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("limit_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("stop_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("tif", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("remaining_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("average_fill_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("last_status_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_status_reference", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "ibkr_execution_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column(
            "sync_run_id",
            sa.Text(),
            sa.ForeignKey("ibkr_sync_runs.sync_run_id"),
            nullable=False,
        ),
        sa.Column("account_ref", sa.Text(), nullable=True),
        sa.Column("execution_id", sa.Text(), nullable=False),
        sa.Column("ibkr_order_id", sa.Integer(), nullable=True),
        sa.Column("ibkr_perm_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("security_type", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("primary_exchange", sa.Text(), nullable=True),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("execution_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("commission", sa.Numeric(18, 6), nullable=True),
        sa.Column("commission_currency", sa.Text(), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(18, 6), nullable=True),
        sa.Column("raw_execution_reference", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ibkr_execution_snapshots")
    op.drop_table("ibkr_open_order_snapshots")
    op.drop_table("ibkr_position_snapshots")
    op.drop_table("ibkr_account_cash_snapshots")
    op.drop_table("ibkr_sync_runs")
