"""broker execution and commission snapshot foundation.

IBKR mirror/reconciliation foundation slice 3.
Imported broker facts only.
No runtime IBKR integration wired yet.
No order transmission wired yet.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_broker_execution_and_commission_snapshots"
down_revision = "0003_broker_position_and_cash_snapshots"
branch_labels = None
depends_on = None

MONEY_NUMERIC = sa.Numeric(precision=20, scale=6)


def upgrade() -> None:
    op.create_table(
        "broker_execution_snapshots",
        sa.Column("broker_execution_snapshot_id", sa.Text(), nullable=False),
        sa.Column("broker_sync_run_id", sa.Text(), nullable=False),
        sa.Column("broker_account_id", sa.Text(), nullable=False),
        sa.Column("broker_system", sa.Text(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_id", sa.Text(), nullable=False),
        sa.Column("order_id", sa.Text(), nullable=True),
        sa.Column("asset_identifier", sa.Text(), nullable=False),
        sa.Column("asset_symbol", sa.Text(), nullable=False),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("quantity", MONEY_NUMERIC, nullable=False),
        sa.Column("price", MONEY_NUMERIC, nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("source_reference_ids_json", sa.JSON(), nullable=True),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "broker_system = 'ibkr'", name="ck_broker_execution_snapshots_broker_system_ibkr"
        ),
        sa.CheckConstraint(
            "execution_id <> ''", name="ck_broker_execution_snapshots_execution_id_not_empty"
        ),
        sa.CheckConstraint(
            "asset_identifier <> ''",
            name="ck_broker_execution_snapshots_asset_identifier_not_empty",
        ),
        sa.CheckConstraint(
            "asset_symbol <> ''", name="ck_broker_execution_snapshots_asset_symbol_not_empty"
        ),
        sa.CheckConstraint(
            "asset_type <> ''", name="ck_broker_execution_snapshots_asset_type_not_empty"
        ),
        sa.CheckConstraint("side <> ''", name="ck_broker_execution_snapshots_side_not_empty"),
        sa.CheckConstraint("quantity > 0", name="ck_broker_execution_snapshots_quantity_gt_0"),
        sa.CheckConstraint("price >= 0", name="ck_broker_execution_snapshots_price_gte_0"),
        sa.CheckConstraint(
            "currency <> ''", name="ck_broker_execution_snapshots_currency_not_empty"
        ),
        sa.CheckConstraint("origin <> ''", name="ck_broker_execution_snapshots_origin_not_empty"),
        sa.CheckConstraint(
            "explanation_nl <> ''", name="ck_broker_execution_snapshots_explanation_nl_not_empty"
        ),
        sa.ForeignKeyConstraint(["broker_sync_run_id"], ["broker_sync_runs.broker_sync_run_id"]),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.broker_account_id"]),
        sa.PrimaryKeyConstraint("broker_execution_snapshot_id"),
    )

    op.create_table(
        "broker_commission_snapshots",
        sa.Column("broker_commission_snapshot_id", sa.Text(), nullable=False),
        sa.Column("broker_sync_run_id", sa.Text(), nullable=False),
        sa.Column("broker_account_id", sa.Text(), nullable=False),
        sa.Column("broker_system", sa.Text(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_id", sa.Text(), nullable=False),
        sa.Column("commission_amount", MONEY_NUMERIC, nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("realized_pnl", MONEY_NUMERIC, nullable=True),
        sa.Column("source_reference_ids_json", sa.JSON(), nullable=True),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "broker_system = 'ibkr'", name="ck_broker_commission_snapshots_broker_system_ibkr"
        ),
        sa.CheckConstraint(
            "execution_id <> ''", name="ck_broker_commission_snapshots_execution_id_not_empty"
        ),
        sa.CheckConstraint(
            "currency <> ''", name="ck_broker_commission_snapshots_currency_not_empty"
        ),
        sa.CheckConstraint(
            "explanation_nl <> ''", name="ck_broker_commission_snapshots_explanation_nl_not_empty"
        ),
        sa.ForeignKeyConstraint(["broker_sync_run_id"], ["broker_sync_runs.broker_sync_run_id"]),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.broker_account_id"]),
        sa.PrimaryKeyConstraint("broker_commission_snapshot_id"),
    )


def downgrade() -> None:
    op.drop_table("broker_commission_snapshots")
    op.drop_table("broker_execution_snapshots")
