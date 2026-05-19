"""broker position and cash snapshot foundation.

IBKR mirror/reconciliation foundation slice 2.
No runtime IBKR integration wired yet.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_broker_position_and_cash_snapshots"
down_revision = "0002_broker_accounts_and_sync_runs"
branch_labels = None
depends_on = None


MONEY_NUMERIC = sa.Numeric(precision=20, scale=6)


def upgrade() -> None:
    op.create_table(
        "broker_position_snapshots",
        sa.Column("broker_position_snapshot_id", sa.Text(), nullable=False),
        sa.Column("broker_sync_run_id", sa.Text(), nullable=False),
        sa.Column("broker_account_id", sa.Text(), nullable=False),
        sa.Column("broker_system", sa.Text(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset_identifier", sa.Text(), nullable=False),
        sa.Column("asset_symbol", sa.Text(), nullable=False),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("quantity", MONEY_NUMERIC, nullable=False),
        sa.Column("average_cost", MONEY_NUMERIC, nullable=True),
        sa.Column("market_value", MONEY_NUMERIC, nullable=True),
        sa.Column("source_data_kind", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("source_reference_ids_json", sa.JSON(), nullable=True),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "broker_system = 'ibkr'", name="ck_broker_position_snapshots_broker_system_ibkr"
        ),
        sa.CheckConstraint(
            "asset_identifier <> ''", name="ck_broker_position_snapshots_asset_identifier_not_empty"
        ),
        sa.CheckConstraint(
            "asset_symbol <> ''", name="ck_broker_position_snapshots_asset_symbol_not_empty"
        ),
        sa.CheckConstraint(
            "asset_type <> ''", name="ck_broker_position_snapshots_asset_type_not_empty"
        ),
        sa.CheckConstraint(
            "currency <> ''", name="ck_broker_position_snapshots_currency_not_empty"
        ),
        sa.CheckConstraint(
            "source_data_kind <> ''", name="ck_broker_position_snapshots_source_data_kind_not_empty"
        ),
        sa.CheckConstraint("origin <> ''", name="ck_broker_position_snapshots_origin_not_empty"),
        sa.CheckConstraint(
            "explanation_nl <> ''", name="ck_broker_position_snapshots_explanation_nl_not_empty"
        ),
        sa.ForeignKeyConstraint(["broker_sync_run_id"], ["broker_sync_runs.broker_sync_run_id"]),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.broker_account_id"]),
        sa.PrimaryKeyConstraint("broker_position_snapshot_id"),
    )

    op.create_table(
        "broker_cash_snapshots",
        sa.Column("broker_cash_snapshot_id", sa.Text(), nullable=False),
        sa.Column("broker_sync_run_id", sa.Text(), nullable=False),
        sa.Column("broker_account_id", sa.Text(), nullable=False),
        sa.Column("broker_system", sa.Text(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("cash_amount", MONEY_NUMERIC, nullable=False),
        sa.Column("source_data_kind", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("source_reference_ids_json", sa.JSON(), nullable=True),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "broker_system = 'ibkr'", name="ck_broker_cash_snapshots_broker_system_ibkr"
        ),
        sa.CheckConstraint("currency <> ''", name="ck_broker_cash_snapshots_currency_not_empty"),
        sa.CheckConstraint(
            "source_data_kind <> ''", name="ck_broker_cash_snapshots_source_data_kind_not_empty"
        ),
        sa.CheckConstraint("origin <> ''", name="ck_broker_cash_snapshots_origin_not_empty"),
        sa.CheckConstraint(
            "explanation_nl <> ''", name="ck_broker_cash_snapshots_explanation_nl_not_empty"
        ),
        sa.ForeignKeyConstraint(["broker_sync_run_id"], ["broker_sync_runs.broker_sync_run_id"]),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.broker_account_id"]),
        sa.PrimaryKeyConstraint("broker_cash_snapshot_id"),
    )


def downgrade() -> None:
    op.drop_table("broker_cash_snapshots")
    op.drop_table("broker_position_snapshots")
