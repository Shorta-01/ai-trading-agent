"""IBKR account-id tagging + connection audit table.

Task 126 — runtime foundation. Adds the ``ibkr_account_id`` column
to every IBKR snapshot table so each row carries the configured
account it was produced from, and adds the append-only
``ibkr_connection_audit`` table that records connection-lifecycle
events (connect_attempt / connect_success / connect_refused /
mode_check_prefix / mode_check_behavioural / disconnect /
session_error).

The new ``ibkr_account_id`` columns ship NULLABLE in this migration
so existing rows + every existing dataclass construction site stay
valid. A follow-up migration (Task 126b) tightens the constraint to
``NOT NULL`` once the API persistence path supplies the value
everywhere.

Also adds ``verified_at`` to ``ibkr_sync_runs`` so the connect-time
two-tier mode check (prefix + behavioural) has a place to land its
verification timestamp.

Revision ID: 0045_ibkr_account_id_and_mode_tagging
Revises: 0044_action_draft_conditional_orders
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0045_ibkr_account_id_and_mode_tagging"
down_revision = "0044_action_draft_conditional_orders"
branch_labels = None
depends_on = None

_SNAPSHOT_TABLES = (
    "ibkr_sync_runs",
    "ibkr_account_cash_snapshots",
    "ibkr_position_snapshots",
    "ibkr_open_order_snapshots",
    "ibkr_execution_snapshots",
)


def upgrade() -> None:
    for table_name in _SNAPSHOT_TABLES:
        op.add_column(
            table_name,
            sa.Column("ibkr_account_id", sa.Text(), nullable=True),
        )
        op.create_index(
            f"ix_{table_name}_ibkr_account_id",
            table_name,
            ["ibkr_account_id"],
        )

    op.add_column(
        "ibkr_sync_runs",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "ibkr_connection_audit",
        sa.Column("audit_id", sa.Text(), primary_key=True),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ibkr_account_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("account_mode_detected", sa.Text(), nullable=True),
        sa.Column("connection_id", sa.Text(), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column(
            "safe_for_action_drafts",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "safe_for_orders",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.CheckConstraint(
            "event_type IN ('connect_attempt','connect_success','connect_refused',"
            "'mode_check_prefix','mode_check_behavioural','disconnect','session_error')",
            name="ck_ibkr_connection_audit_event_type",
        ),
        sa.CheckConstraint(
            "account_mode_detected IS NULL OR "
            "account_mode_detected IN ('paper','live','unknown')",
            name="ck_ibkr_connection_audit_account_mode_detected",
        ),
    )
    op.create_index(
        "ix_ibkr_connection_audit_account_event",
        "ibkr_connection_audit",
        ["ibkr_account_id", "event_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ibkr_connection_audit_account_event",
        table_name="ibkr_connection_audit",
    )
    op.drop_table("ibkr_connection_audit")

    op.drop_column("ibkr_sync_runs", "verified_at")

    for table_name in reversed(_SNAPSHOT_TABLES):
        op.drop_index(
            f"ix_{table_name}_ibkr_account_id",
            table_name=table_name,
        )
        op.drop_column(table_name, "ibkr_account_id")
