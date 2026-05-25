"""Task 127: scheduled-run audit + per-worker scheduler state.

Adds the two tables that the APScheduler skeleton needs to record
its runs durably:

* ``scheduled_run_audit`` — append-only one-row-per-fire audit
  capturing the detected mode + outcome + next-scheduled time.
  Locked CHECK constraints on ``run_type`` / ``mode_detected`` /
  ``outcome`` per Task 127 product locks §5.
* ``scheduler_state`` — one row per running worker process; the
  scheduler heartbeats this row every 60 seconds with the next
  fire times for the two cron jobs (pre-briefing + hourly).

Both tables ship with safety booleans hard-False where applicable
per project doctrine.

Revision ID: 0046_scheduled_run_audit_and_scheduler_state
Revises: 0045_ibkr_account_id_and_mode_tagging
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0046_scheduled_run_audit_and_scheduler_state"
down_revision = "0045_ibkr_account_id_and_mode_tagging"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduled_run_audit",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("run_type", sa.Text(), nullable=False),
        sa.Column("ibkr_account_id", sa.Text(), nullable=True),
        sa.Column("mode_detected", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("error_details_json", sa.JSON(), nullable=True),
        sa.Column(
            "next_scheduled_at", sa.DateTime(timezone=True), nullable=True
        ),
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
            "run_type IN ('pre_briefing','morning_briefing','hourly_delta')",
            name="ck_scheduled_run_audit_run_type",
        ),
        sa.CheckConstraint(
            "mode_detected IN ('cold_start','normal','disconnected',"
            "'skipped_locked','skipped_disabled')",
            name="ck_scheduled_run_audit_mode_detected",
        ),
        sa.CheckConstraint(
            "outcome IN ('completed','error')",
            name="ck_scheduled_run_audit_outcome",
        ),
    )
    op.create_index(
        "ix_scheduled_run_audit_run_at",
        "scheduled_run_audit",
        [sa.text("run_at DESC")],
    )
    op.create_index(
        "ix_scheduled_run_audit_run_type",
        "scheduled_run_audit",
        ["run_type"],
    )

    op.create_table(
        "scheduler_state",
        sa.Column("worker_id", sa.Text(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_heartbeat_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "next_pre_briefing_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "next_hourly_at", sa.DateTime(timezone=True), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_table("scheduler_state")
    op.drop_index(
        "ix_scheduled_run_audit_run_type",
        table_name="scheduled_run_audit",
    )
    op.drop_index(
        "ix_scheduled_run_audit_run_at",
        table_name="scheduled_run_audit",
    )
    op.drop_table("scheduled_run_audit")
