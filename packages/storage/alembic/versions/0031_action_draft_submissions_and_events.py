"""action draft submissions + events durable storage.

Revision ID: 0031_action_draft_submissions_and_events
Revises: 0030_asset_action_drafts
Create Date: 2026-05-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0031_action_draft_submissions_and_events"
down_revision = "0030_asset_action_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_action_draft_submissions",
        sa.Column("submission_id", sa.Text(), primary_key=True),
        sa.Column("draft_id", sa.Text(), nullable=False, unique=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("approval_status", sa.Text(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Text(), nullable=True),
        sa.Column("approval_dry_run_status", sa.Text(), nullable=True),
        sa.Column("approval_dry_run_failures_json", sa.JSON(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ibkr_order_id", sa.Integer(), nullable=True),
        sa.Column("ibkr_perm_id", sa.Integer(), nullable=True),
        sa.Column("ibkr_client_id", sa.Integer(), nullable=True),
        sa.Column("ibkr_status_text", sa.Text(), nullable=True),
        sa.Column("filled_quantity", sa.Numeric(20, 6), nullable=True),
        sa.Column("remaining_quantity", sa.Numeric(20, 6), nullable=True),
        sa.Column("average_fill_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("rejected_reason", sa.Text(), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("account_mode", sa.Text(), nullable=False),
        sa.Column("expected_account_mode", sa.Text(), nullable=False),
        sa.Column("provider_code", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_state_transition_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "safe_for_broker_submission",
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
    )

    op.create_table(
        "asset_action_draft_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("draft_id", sa.Text(), nullable=False),
        sa.Column("submission_id", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("from_state", sa.Text(), nullable=True),
        sa.Column("to_state", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rationale_nl", sa.Text(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("asset_action_draft_events")
    op.drop_table("asset_action_draft_submissions")
