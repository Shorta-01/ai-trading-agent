"""Task 135: Reconciliation audit + manual review queue + unmatched executions.

Adds the storage layer for the reconciliation worker that heals
divergence between system state and IBKR's broker truth (Task 135
product lock §1). Four new append-only-ish tables:

* ``reconciliation_audit`` — one row per reconciler action across
  Pass A (orphaned executions), Pass B (stale in-flight), and
  Pass C (timeout recovery). The ``ibkr_evidence_json`` column
  captures the raw IBKR response that justified the heal.
* ``unmatched_execution_audit`` — IBKR executions for which no draft
  exists in our system (e.g. the user placed an order manually in
  TWS while our worker was online). UNIQUE on ``ibkr_exec_id`` so
  duplicate detections are guaranteed idempotent.
* ``manual_review_queue`` — drafts the reconciler couldn't heal
  automatically (timeouts older than 24h or terminal-state
  divergence per Task 135 product lock §4). User can acknowledge via
  the API; the underlying draft status is not mutated by the
  acknowledgement.
* ``reconciliation_run_audit`` — one row per reconciler tick with
  start + completion timestamps and per-pass counts.

Also widens ``action_drafts.status`` with the new
``requires_manual_review`` terminal status (Task 135 product lock §3
Pass C escalation path).

Revision ID: 0053_reconciliation_audit_and_manual_review
Revises: 0052_ibkr_submission_lifecycle_audit_and_executions
Create Date: 2026-05-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0053_reconciliation_audit_and_manual_review"
down_revision = "0052_ibkr_submission_lifecycle_audit_and_executions"
branch_labels = None
depends_on = None

_PRICE = sa.Numeric(precision=20, scale=8)


# Mirror of the locked status set after 135 widening. Kept in this
# migration so the upgrade + downgrade paths are self-describing.
_EXTENDED_STATUS_VALUES = (
    "'proposed', 'edited', 'user_approved', 'dismissed', 'deleted', "
    "'superseded', 'submitted', 'accepted', 'working', 'filled', "
    "'partially_filled', 'cancelled', 'rejected', "
    "'pending_cancellation', 'awaiting_reply_timeout', "
    "'requires_manual_review'"
)
_PRE_135_STATUS_VALUES = (
    "'proposed', 'edited', 'user_approved', 'dismissed', 'deleted', "
    "'superseded', 'submitted', 'accepted', 'working', 'filled', "
    "'partially_filled', 'cancelled', 'rejected', "
    "'pending_cancellation', 'awaiting_reply_timeout'"
)


def upgrade() -> None:
    # 1. Widen action_drafts.status with requires_manual_review.
    with op.batch_alter_table("action_drafts") as batch_op:
        batch_op.drop_constraint(
            "ck_action_drafts_status", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_action_drafts_status",
            f"status IN ({_EXTENDED_STATUS_VALUES})",
        )

    # 2. reconciliation_audit — one row per reconciler action.
    op.create_table(
        "reconciliation_audit",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column(
            "reconciliation_run_id", sa.Text(), nullable=False
        ),
        sa.Column(
            "action_draft_id",
            sa.Text(),
            sa.ForeignKey("action_drafts.action_draft_id"),
            nullable=True,
        ),
        sa.Column(
            "event_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("pass_name", sa.Text(), nullable=False),
        sa.Column("divergence_type", sa.Text(), nullable=False),
        sa.Column("before_status", sa.Text(), nullable=True),
        sa.Column("after_status", sa.Text(), nullable=True),
        sa.Column("ibkr_evidence_json", sa.JSON(), nullable=False),
        sa.Column("notes_dutch", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "pass_name IN ('orphaned_execution', 'stale_in_flight', "
            "'timeout_recovery')",
            name="ck_reconciliation_audit_pass_name",
        ),
        sa.CheckConstraint(
            "divergence_type IN ("
            "'missing_execution_applied', "
            "'status_corrected_to_filled', "
            "'status_corrected_to_cancelled', "
            "'status_corrected_to_rejected', "
            "'status_corrected_to_partially_filled', "
            "'timeout_recovered_to_terminal', "
            "'timeout_flagged_manual_review', "
            "'unmatched_execution', "
            "'terminal_state_divergence_logged')",
            name="ck_reconciliation_audit_divergence_type",
        ),
    )
    op.create_index(
        "ix_reconciliation_audit_run",
        "reconciliation_audit",
        ["reconciliation_run_id"],
    )
    op.create_index(
        "ix_reconciliation_audit_draft_event",
        "reconciliation_audit",
        ["action_draft_id", "event_at"],
    )

    # 3. unmatched_execution_audit — UNIQUE on ibkr_exec_id.
    op.create_table(
        "unmatched_execution_audit",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column(
            "event_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("ibkr_perm_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "ibkr_exec_id", sa.Text(), nullable=False, unique=True
        ),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("conid", sa.Text(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("fill_price_local", _PRICE, nullable=False),
        sa.Column("fill_quantity", _PRICE, nullable=False),
        sa.Column(
            "fill_time", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("raw_execution_json", sa.JSON(), nullable=False),
        sa.Column(
            "resolution_status",
            sa.Text(),
            nullable=False,
            server_default="unresolved",
        ),
        sa.CheckConstraint(
            "side IN ('BUY', 'SELL')",
            name="ck_unmatched_execution_audit_side",
        ),
        sa.CheckConstraint(
            "resolution_status IN ('unresolved', 'manually_matched', "
            "'ignored')",
            name="ck_unmatched_execution_audit_resolution_status",
        ),
        sa.CheckConstraint(
            "fill_price_local > 0",
            name="ck_unmatched_execution_audit_fill_price_positive",
        ),
        sa.CheckConstraint(
            "fill_quantity > 0",
            name="ck_unmatched_execution_audit_fill_quantity_positive",
        ),
    )
    op.create_index(
        "ix_unmatched_execution_audit_account",
        "unmatched_execution_audit",
        ["account_id", "fill_time"],
    )

    # 4. manual_review_queue — flagged drafts pending user attention.
    op.create_table(
        "manual_review_queue",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column(
            "flagged_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "action_draft_id",
            sa.Text(),
            sa.ForeignKey("action_drafts.action_draft_id"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("details_dutch", sa.Text(), nullable=False),
        sa.Column(
            "resolution_status",
            sa.Text(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "resolved_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "reason IN ('timeout_24h_no_data', "
            "'terminal_state_divergence', "
            "'unmatched_execution_no_draft')",
            name="ck_manual_review_queue_reason",
        ),
        sa.CheckConstraint(
            "resolution_status IN ('pending', 'resolved', "
            "'acknowledged')",
            name="ck_manual_review_queue_resolution_status",
        ),
    )
    op.create_index(
        "ix_manual_review_queue_status",
        "manual_review_queue",
        ["resolution_status", "flagged_at"],
    )
    op.create_index(
        "ix_manual_review_queue_draft",
        "manual_review_queue",
        ["action_draft_id"],
    )

    # 5. reconciliation_run_audit — one row per reconciler tick.
    op.create_table(
        "reconciliation_run_audit",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column(
            "reconciliation_run_id",
            sa.Text(),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column(
            "pass_a_orphaned_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "pass_b_stale_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "pass_c_timeout_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "divergences_found",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("mode_detected", sa.Text(), nullable=False),
        sa.Column("error_details_json", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "mode_detected IN ('completed', 'skipped_locked', "
            "'skipped_disconnected', 'error')",
            name="ck_reconciliation_run_audit_mode_detected",
        ),
    )
    op.create_index(
        "ix_reconciliation_run_audit_account_started",
        "reconciliation_run_audit",
        ["account_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reconciliation_run_audit_account_started",
        table_name="reconciliation_run_audit",
    )
    op.drop_table("reconciliation_run_audit")

    op.drop_index(
        "ix_manual_review_queue_draft", table_name="manual_review_queue"
    )
    op.drop_index(
        "ix_manual_review_queue_status", table_name="manual_review_queue"
    )
    op.drop_table("manual_review_queue")

    op.drop_index(
        "ix_unmatched_execution_audit_account",
        table_name="unmatched_execution_audit",
    )
    op.drop_table("unmatched_execution_audit")

    op.drop_index(
        "ix_reconciliation_audit_draft_event",
        table_name="reconciliation_audit",
    )
    op.drop_index(
        "ix_reconciliation_audit_run",
        table_name="reconciliation_audit",
    )
    op.drop_table("reconciliation_audit")

    with op.batch_alter_table("action_drafts") as batch_op:
        batch_op.drop_constraint(
            "ck_action_drafts_status", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_action_drafts_status",
            f"status IN ({_PRE_135_STATUS_VALUES})",
        )
