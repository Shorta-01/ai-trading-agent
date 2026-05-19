"""broker account and sync run foundation.

IBKR mirror/reconciliation foundation slice 1.
No runtime IBKR integration wired yet.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_broker_accounts_and_sync_runs"
down_revision = "0001_paper_setup_audit_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broker_accounts",
        sa.Column("broker_account_id", sa.Text(), nullable=False),
        sa.Column("broker_system", sa.Text(), nullable=False),
        sa.Column("ibkr_account_ref", sa.Text(), nullable=True),
        sa.Column("account_label", sa.Text(), nullable=False),
        sa.Column("account_mode", sa.Text(), nullable=False),
        sa.Column("connection_status", sa.Text(), nullable=False),
        sa.Column("configured", sa.Boolean(), nullable=False),
        sa.Column("paper_account", sa.Boolean(), nullable=False),
        sa.Column("live_trading_allowed", sa.Boolean(), nullable=False),
        sa.Column("source_of_truth_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint("broker_system = 'ibkr'", name="ck_broker_accounts_broker_system_ibkr"),
        sa.CheckConstraint(
            "live_trading_allowed IS FALSE",
            name="ck_broker_accounts_live_trading_allowed_false",
        ),
        sa.CheckConstraint(
            "account_label <> ''",
            name="ck_broker_accounts_account_label_not_empty",
        ),
        sa.CheckConstraint("account_mode <> ''", name="ck_broker_accounts_account_mode_not_empty"),
        sa.CheckConstraint(
            "connection_status <> ''",
            name="ck_broker_accounts_connection_status_not_empty",
        ),
        sa.CheckConstraint(
            "source_of_truth_status <> ''",
            name="ck_broker_accounts_source_of_truth_status_not_empty",
        ),
        sa.CheckConstraint(
            "explanation_nl <> ''",
            name="ck_broker_accounts_explanation_nl_not_empty",
        ),
        sa.PrimaryKeyConstraint("broker_account_id"),
    )

    op.create_table(
        "broker_sync_runs",
        sa.Column("broker_sync_run_id", sa.Text(), nullable=False),
        sa.Column("broker_account_id", sa.Text(), nullable=True),
        sa.Column("broker_system", sa.Text(), nullable=False),
        sa.Column("sync_mode", sa.Text(), nullable=False),
        sa.Column("sync_status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_data_kinds_json", sa.JSON(), nullable=True),
        sa.Column("data_source_types_json", sa.JSON(), nullable=True),
        sa.Column("requires_ibkr_configuration", sa.Boolean(), nullable=False),
        sa.Column("requires_broker_session", sa.Boolean(), nullable=False),
        sa.Column("blocks_suggestions_until_complete", sa.Boolean(), nullable=False),
        sa.Column("summary_nl", sa.Text(), nullable=False),
        sa.Column("help_nl", sa.Text(), nullable=False),
        sa.CheckConstraint("broker_system = 'ibkr'", name="ck_broker_sync_runs_broker_system_ibkr"),
        sa.CheckConstraint("sync_mode <> ''", name="ck_broker_sync_runs_sync_mode_not_empty"),
        sa.CheckConstraint("sync_status <> ''", name="ck_broker_sync_runs_sync_status_not_empty"),
        sa.CheckConstraint("summary_nl <> ''", name="ck_broker_sync_runs_summary_nl_not_empty"),
        sa.CheckConstraint("help_nl <> ''", name="ck_broker_sync_runs_help_nl_not_empty"),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="ck_broker_sync_runs_completed_at_after_started_at",
        ),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.broker_account_id"]),
        sa.PrimaryKeyConstraint("broker_sync_run_id"),
    )


def downgrade() -> None:
    op.drop_table("broker_sync_runs")
    op.drop_table("broker_accounts")
