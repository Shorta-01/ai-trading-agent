"""Task 133: Action Drafts + Action Draft Audit.

Adds the user-facing ``action_drafts`` table — a prefilled IBKR-format
order proposal derived from a non-Geblokkeerd Decision Package plus the
current IBKR cash/position context. Editable until the user approves;
after that it's immutable (Task 133 product lock §3).

Also adds the append-only ``action_draft_audit`` table mirroring the
Task 132 Decision Package chain pattern — one row per status transition
or field edit.

Safety boolean ``safe_for_submission`` is hard-False at the DB CHECK
layer; Task 134 (the actual submission task) is the only code path
allowed to flip it conditionally.

Revision ID: 0051_action_drafts_and_audit
Revises: 0050_decision_packages
Create Date: 2026-05-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0051_action_drafts_and_audit"
down_revision = "0050_decision_packages"
branch_labels = None
depends_on = None

_PRICE = sa.Numeric(precision=20, scale=8)


def upgrade() -> None:
    op.create_table(
        "action_drafts",
        sa.Column("action_draft_id", sa.Text(), primary_key=True),
        sa.Column(
            "decision_package_id",
            sa.Text(),
            sa.ForeignKey("decision_packages.decision_package_id"),
            nullable=True,
        ),
        sa.Column("forecast_run_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("ibkr_account_id", sa.Text(), nullable=False),
        sa.Column("conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("currency_local", sa.Text(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("quantity", _PRICE, nullable=False),
        sa.Column("order_type", sa.Text(), nullable=False),
        sa.Column("limit_price_local", _PRICE, nullable=False),
        sa.Column("time_in_force", sa.Text(), nullable=False),
        sa.Column("notional_local", _PRICE, nullable=False),
        sa.Column("notional_eur", _PRICE, nullable=False),
        sa.Column("fx_rate_at_creation", _PRICE, nullable=False),
        sa.Column("usable_cash_eur_at_creation", _PRICE, nullable=False),
        sa.Column("held_quantity_at_creation", _PRICE, nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "last_edited_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "user_approved_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "dismissed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "deleted_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("dismissed_reason", sa.Text(), nullable=True),
        sa.Column("user_note", sa.Text(), nullable=True),
        sa.Column(
            "superseded_by_decision_package_id",
            sa.Text(),
            sa.ForeignKey("decision_packages.decision_package_id"),
            nullable=True,
        ),
        sa.Column("audit_trail_hash", sa.Text(), nullable=False),
        sa.Column("previous_draft_hash", sa.Text(), nullable=True),
        sa.Column(
            "safe_for_submission",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.CheckConstraint(
            "created_by IN ('user', 'system')",
            name="ck_action_drafts_created_by",
        ),
        sa.CheckConstraint(
            "side IN ('BUY', 'SELL')",
            name="ck_action_drafts_side",
        ),
        sa.CheckConstraint(
            "order_type IN ('LMT')",
            name="ck_action_drafts_order_type",
        ),
        sa.CheckConstraint(
            "time_in_force IN ('DAY')",
            name="ck_action_drafts_time_in_force",
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'edited', 'user_approved', "
            "'dismissed', 'deleted', 'superseded')",
            name="ck_action_drafts_status",
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_action_drafts_quantity_positive",
        ),
        sa.CheckConstraint(
            "limit_price_local > 0",
            name="ck_action_drafts_limit_price_positive",
        ),
        sa.CheckConstraint(
            "safe_for_submission = FALSE",
            name="ck_action_drafts_safe_for_submission_false",
        ),
    )
    op.create_index(
        "ix_action_drafts_account_status_created",
        "action_drafts",
        ["ibkr_account_id", "status", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_action_drafts_decision_package_id",
        "action_drafts",
        ["decision_package_id"],
    )
    op.create_index(
        "ix_action_drafts_conid_account_status",
        "action_drafts",
        ["conid", "ibkr_account_id", "status"],
    )

    op.create_table(
        "action_draft_audit",
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
            "event_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("before_state_json", sa.JSON(), nullable=True),
        sa.Column("after_state_json", sa.JSON(), nullable=True),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('created', 'edited', 'approved', "
            "'dismissed', 'deleted', 'superseded')",
            name="ck_action_draft_audit_event_type",
        ),
        sa.CheckConstraint(
            "actor IN ('user', 'system')",
            name="ck_action_draft_audit_actor",
        ),
    )
    op.create_index(
        "ix_action_draft_audit_draft_id_event_at",
        "action_draft_audit",
        ["action_draft_id", "event_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_action_draft_audit_draft_id_event_at",
        table_name="action_draft_audit",
    )
    op.drop_table("action_draft_audit")
    op.drop_index(
        "ix_action_drafts_conid_account_status",
        table_name="action_drafts",
    )
    op.drop_index(
        "ix_action_drafts_decision_package_id",
        table_name="action_drafts",
    )
    op.drop_index(
        "ix_action_drafts_account_status_created",
        table_name="action_drafts",
    )
    op.drop_table("action_drafts")
