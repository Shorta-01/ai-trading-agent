"""Task 134: IBKR submission lifecycle audit, executions, behavioural guardrails.

Extends ``action_drafts`` with the in-flight + terminal IBKR statuses
that Stage 3 of the locked three-stage action flow needs
(``submitted``/``accepted``/``working``/``filled``/``partially_filled``/
``cancelled``/``rejected``/``pending_cancellation``/
``awaiting_reply_timeout``), plus three new columns:
``submission_block_reason`` (locked enum), ``submission_started_at``,
``terminal_state_at``.

Adds four append-only tables:

* ``ibkr_submission_audit`` — one row per ``placeOrder()`` attempt.
* ``ibkr_submission_lifecycle`` — one row per IBKR callback event
  (status change, fill, commission report, cancellation request).
* ``ibkr_executions`` — one row per fill (uniqueness on
  ``ibkr_exec_id``).
* ``behavioural_guardrail_settings`` — per-account thresholds (60s
  cooldown / 5 per day / 5%-5d soft drawdown / 10%-20d hard drawdown
  / 1.5% FOMO drift) per the brainstorm lock.

``safe_for_submission`` on ``action_drafts`` stays hard-False at the
CHECK layer — Task 134's actual submitter (Task 134b) is the only
code path allowed to flip it conditionally, and only via the
status-machine transition rather than a direct UPDATE.

Revision ID: 0052_ibkr_submission_lifecycle_audit_and_executions
Revises: 0051_action_drafts_and_audit
Create Date: 2026-05-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0052_ibkr_submission_lifecycle_audit_and_executions"
down_revision = "0051_action_drafts_and_audit"
branch_labels = None
depends_on = None

_PRICE = sa.Numeric(precision=20, scale=8)
_PCT = sa.Numeric(precision=8, scale=4)

_EXTENDED_STATUS_VALUES = (
    "'proposed', 'edited', 'user_approved', 'dismissed', 'deleted', "
    "'superseded', 'submitted', 'accepted', 'working', 'filled', "
    "'partially_filled', 'cancelled', 'rejected', "
    "'pending_cancellation', 'awaiting_reply_timeout'"
)

_BLOCK_REASON_VALUES = (
    "'cash_insufficient', 'mode_mismatch', 'connection_down', "
    "'account_id_mismatch', 'duplicate_in_flight', 'market_closed', "
    "'cooldown', 'daily_limit', 'soft_drawdown', 'hard_drawdown', "
    "'fomo', 'tick_size_invalid', 'unknown'"
)


def upgrade() -> None:
    # 1. Widen action_drafts.status enum + add three new lifecycle columns.
    with op.batch_alter_table("action_drafts") as batch_op:
        batch_op.drop_constraint(
            "ck_action_drafts_status", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_action_drafts_status",
            f"status IN ({_EXTENDED_STATUS_VALUES})",
        )
        batch_op.add_column(
            sa.Column("submission_block_reason", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "submission_started_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "terminal_state_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.create_check_constraint(
            "ck_action_drafts_submission_block_reason",
            f"submission_block_reason IS NULL OR submission_block_reason "
            f"IN ({_BLOCK_REASON_VALUES})",
        )

    # 2. ibkr_submission_audit — one row per placeOrder() attempt.
    op.create_table(
        "ibkr_submission_audit",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column(
            "action_draft_id",
            sa.Text(),
            sa.ForeignKey("action_drafts.action_draft_id"),
            nullable=False,
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("sent_to_account_id", sa.Text(), nullable=False),
        sa.Column("sent_account_mode", sa.Text(), nullable=False),
        sa.Column("ibkr_perm_id", sa.BigInteger(), nullable=True),
        sa.Column("ibkr_order_id", sa.Integer(), nullable=True),
        sa.Column("contract_json", sa.JSON(), nullable=False),
        sa.Column("order_json", sa.JSON(), nullable=False),
        sa.Column("gateway_session_id", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("error_class", sa.Text(), nullable=True),
        sa.Column("error_message_dutch", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "sent_account_mode IN ('paper', 'live')",
            name="ck_ibkr_submission_audit_sent_account_mode",
        ),
        sa.CheckConstraint(
            "result IN ('placed', 'rejected_at_send', 'connection_lost')",
            name="ck_ibkr_submission_audit_result",
        ),
    )
    op.create_index(
        "ix_ibkr_submission_audit_draft_submitted",
        "ibkr_submission_audit",
        ["action_draft_id", "submitted_at"],
    )
    op.create_index(
        "ix_ibkr_submission_audit_account_submitted",
        "ibkr_submission_audit",
        ["sent_to_account_id", "submitted_at"],
    )

    # 3. ibkr_submission_lifecycle — IBKR-callback event log.
    op.create_table(
        "ibkr_submission_lifecycle",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column(
            "action_draft_id",
            sa.Text(),
            sa.ForeignKey("action_drafts.action_draft_id"),
            nullable=False,
        ),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ibkr_perm_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("from_status", sa.Text(), nullable=True),
        sa.Column("to_status", sa.Text(), nullable=True),
        sa.Column("ibkr_raw_status", sa.Text(), nullable=True),
        sa.Column("fill_price_local", _PRICE, nullable=True),
        sa.Column("fill_quantity", _PRICE, nullable=True),
        sa.Column("commission", _PRICE, nullable=True),
        sa.Column("commission_currency", sa.Text(), nullable=True),
        sa.Column("raw_callback_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('status_change', 'fill', "
            "'commission_report', 'cancellation_request')",
            name="ck_ibkr_submission_lifecycle_event_type",
        ),
    )
    op.create_index(
        "ix_ibkr_submission_lifecycle_draft_event_at",
        "ibkr_submission_lifecycle",
        ["action_draft_id", "event_at"],
    )
    op.create_index(
        "ix_ibkr_submission_lifecycle_perm_id",
        "ibkr_submission_lifecycle",
        ["ibkr_perm_id"],
    )

    # 4. ibkr_executions — one row per fill.
    op.create_table(
        "ibkr_executions",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column(
            "ibkr_exec_id", sa.Text(), nullable=False, unique=True
        ),
        sa.Column("ibkr_perm_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "action_draft_id",
            sa.Text(),
            sa.ForeignKey("action_drafts.action_draft_id"),
            nullable=False,
        ),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("conid", sa.Text(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("fill_price_local", _PRICE, nullable=False),
        sa.Column("fill_quantity", _PRICE, nullable=False),
        sa.Column("fill_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("commission", _PRICE, nullable=False),
        sa.Column("commission_currency", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "side IN ('BUY', 'SELL')",
            name="ck_ibkr_executions_side",
        ),
        sa.CheckConstraint(
            "fill_price_local > 0",
            name="ck_ibkr_executions_fill_price_positive",
        ),
        sa.CheckConstraint(
            "fill_quantity > 0",
            name="ck_ibkr_executions_fill_quantity_positive",
        ),
        sa.CheckConstraint(
            "commission >= 0",
            name="ck_ibkr_executions_commission_non_negative",
        ),
    )
    op.create_index(
        "ix_ibkr_executions_account_conid_time",
        "ibkr_executions",
        ["account_id", "conid", "fill_time"],
    )
    op.create_index(
        "ix_ibkr_executions_action_draft_id",
        "ibkr_executions",
        ["action_draft_id"],
    )
    op.create_index(
        "ix_ibkr_executions_perm_id",
        "ibkr_executions",
        ["ibkr_perm_id"],
    )

    # 5. behavioural_guardrail_settings — per-account thresholds.
    op.create_table(
        "behavioural_guardrail_settings",
        sa.Column("ibkr_account_id", sa.Text(), primary_key=True),
        sa.Column(
            "daily_max_approvals",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
        sa.Column(
            "cooldown_seconds",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
        sa.Column(
            "anti_revenge_window_hours",
            sa.Integer(),
            nullable=False,
            server_default="72",
        ),
        sa.Column(
            "anti_revenge_loss_threshold_pct",
            _PCT,
            nullable=False,
            server_default="1.0",
        ),
        sa.Column(
            "soft_drawdown_pct",
            _PCT,
            nullable=False,
            server_default="5.0",
        ),
        sa.Column(
            "soft_drawdown_window_days",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
        sa.Column(
            "hard_drawdown_pct",
            _PCT,
            nullable=False,
            server_default="10.0",
        ),
        sa.Column(
            "hard_drawdown_window_days",
            sa.Integer(),
            nullable=False,
            server_default="20",
        ),
        sa.Column(
            "fomo_drift_pct",
            _PCT,
            nullable=False,
            server_default="1.5",
        ),
        sa.Column(
            "last_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "daily_max_approvals > 0",
            name="ck_behavioural_guardrail_daily_max_positive",
        ),
        sa.CheckConstraint(
            "cooldown_seconds >= 0",
            name="ck_behavioural_guardrail_cooldown_non_negative",
        ),
        sa.CheckConstraint(
            "anti_revenge_loss_threshold_pct >= 0",
            name="ck_behavioural_guardrail_anti_revenge_non_negative",
        ),
        sa.CheckConstraint(
            "soft_drawdown_pct >= 0",
            name="ck_behavioural_guardrail_soft_drawdown_non_negative",
        ),
        sa.CheckConstraint(
            "hard_drawdown_pct >= 0",
            name="ck_behavioural_guardrail_hard_drawdown_non_negative",
        ),
        sa.CheckConstraint(
            "fomo_drift_pct >= 0",
            name="ck_behavioural_guardrail_fomo_non_negative",
        ),
    )


def downgrade() -> None:
    op.drop_table("behavioural_guardrail_settings")

    op.drop_index(
        "ix_ibkr_executions_perm_id", table_name="ibkr_executions"
    )
    op.drop_index(
        "ix_ibkr_executions_action_draft_id", table_name="ibkr_executions"
    )
    op.drop_index(
        "ix_ibkr_executions_account_conid_time",
        table_name="ibkr_executions",
    )
    op.drop_table("ibkr_executions")

    op.drop_index(
        "ix_ibkr_submission_lifecycle_perm_id",
        table_name="ibkr_submission_lifecycle",
    )
    op.drop_index(
        "ix_ibkr_submission_lifecycle_draft_event_at",
        table_name="ibkr_submission_lifecycle",
    )
    op.drop_table("ibkr_submission_lifecycle")

    op.drop_index(
        "ix_ibkr_submission_audit_account_submitted",
        table_name="ibkr_submission_audit",
    )
    op.drop_index(
        "ix_ibkr_submission_audit_draft_submitted",
        table_name="ibkr_submission_audit",
    )
    op.drop_table("ibkr_submission_audit")

    # Restore the Task 133 action_drafts status enum + drop the three
    # new lifecycle columns + the block_reason CHECK constraint.
    with op.batch_alter_table("action_drafts") as batch_op:
        batch_op.drop_constraint(
            "ck_action_drafts_submission_block_reason", type_="check"
        )
        batch_op.drop_column("terminal_state_at")
        batch_op.drop_column("submission_started_at")
        batch_op.drop_column("submission_block_reason")
        batch_op.drop_constraint(
            "ck_action_drafts_status", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_action_drafts_status",
            "status IN ('proposed', 'edited', 'user_approved', "
            "'dismissed', 'deleted', 'superseded')",
        )
