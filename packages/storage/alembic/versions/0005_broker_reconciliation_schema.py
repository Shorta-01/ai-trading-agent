"""Broker reconciliation schema foundation.

IBKR mirror/reconciliation foundation slice 4.
Reconciliation status/difference storage only.
No runtime IBKR integration wired yet.
No reconciliation engine wired yet.
No order transmission wired yet.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "broker_reconciliation_reports",
        sa.Column("broker_reconciliation_report_id", sa.Text(), nullable=False),
        sa.Column("broker_sync_run_id", sa.Text(), nullable=False),
        sa.Column("broker_account_id", sa.Text(), nullable=True),
        sa.Column("broker_system", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("suggestion_policy", sa.Text(), nullable=False),
        sa.Column("can_create_suggestions", sa.Boolean(), nullable=False),
        sa.Column("can_create_orders", sa.Boolean(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title_nl", sa.Text(), nullable=False),
        sa.Column("summary_nl", sa.Text(), nullable=False),
        sa.Column("help_nl", sa.Text(), nullable=False),
        sa.CheckConstraint("broker_system = 'ibkr'", name="ck_brr_broker_system_ibkr"),
        sa.CheckConstraint("can_create_orders IS FALSE", name="ck_brr_can_create_orders_false"),
        sa.CheckConstraint("status <> ''", name="ck_brr_status_not_empty"),
        sa.CheckConstraint(
            "suggestion_policy <> ''", name="ck_brr_suggestion_policy_not_empty"
        ),
        sa.CheckConstraint("title_nl <> ''", name="ck_brr_title_nl_not_empty"),
        sa.CheckConstraint("summary_nl <> ''", name="ck_brr_summary_nl_not_empty"),
        sa.CheckConstraint("help_nl <> ''", name="ck_brr_help_nl_not_empty"),
        sa.ForeignKeyConstraint(["broker_sync_run_id"], ["broker_sync_runs.broker_sync_run_id"]),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.broker_account_id"]),
        sa.PrimaryKeyConstraint("broker_reconciliation_report_id"),
    )

    op.create_table(
        "broker_reconciliation_differences",
        sa.Column("broker_reconciliation_difference_id", sa.Text(), nullable=False),
        sa.Column("broker_reconciliation_report_id", sa.Text(), nullable=False),
        sa.Column("broker_account_id", sa.Text(), nullable=False),
        sa.Column("broker_system", sa.Text(), nullable=False),
        sa.Column("difference_kind", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("broker_value", sa.Text(), nullable=True),
        sa.Column("local_value", sa.Text(), nullable=True),
        sa.Column("asset_identifier", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("blocks_suggestions", sa.Boolean(), nullable=False),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False),
        sa.Column("summary_nl", sa.Text(), nullable=False),
        sa.Column("help_nl", sa.Text(), nullable=False),
        sa.Column("source_reference_ids_json", sa.JSON(), nullable=True),
        sa.Column("audit_event_ids_json", sa.JSON(), nullable=True),
        sa.CheckConstraint("broker_system = 'ibkr'", name="ck_brd_broker_system_ibkr"),
        sa.CheckConstraint("difference_kind <> ''", name="ck_brd_difference_kind_not_empty"),
        sa.CheckConstraint("severity <> ''", name="ck_brd_severity_not_empty"),
        sa.CheckConstraint(
            "severity NOT IN ('blocking', 'critical') OR blocks_suggestions IS TRUE",
            name="ck_brd_blocking_or_critical_requires_block",
        ),
        sa.CheckConstraint("summary_nl <> ''", name="ck_brd_summary_nl_not_empty"),
        sa.CheckConstraint("help_nl <> ''", name="ck_brd_help_nl_not_empty"),
        sa.ForeignKeyConstraint(
            ["broker_reconciliation_report_id"],
            ["broker_reconciliation_reports.broker_reconciliation_report_id"],
        ),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.broker_account_id"]),
        sa.PrimaryKeyConstraint("broker_reconciliation_difference_id"),
    )


def downgrade() -> None:
    op.drop_table("broker_reconciliation_differences")
    op.drop_table("broker_reconciliation_reports")
