"""daily briefings + briefing alerts.

Revision ID: 0036_daily_briefings
Revises: 0035_action_draft_belgian_tob
Create Date: 2026-05-31
"""

import sqlalchemy as sa
from alembic import op

revision = "0036_daily_briefings"
down_revision = "0035_action_draft_belgian_tob"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_briefings",
        sa.Column("briefing_id", sa.Text(), primary_key=True),
        sa.Column("briefing_date", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lookback_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("position_count", sa.Integer(), nullable=False),
        sa.Column("base_currency", sa.Text(), nullable=True),
        sa.Column("total_position_value", sa.Numeric(20, 6), nullable=True),
        sa.Column("cash_total", sa.Numeric(20, 6), nullable=True),
        sa.Column("fx_freshness_status", sa.Text(), nullable=True),
        sa.Column("new_suggestion_count", sa.Integer(), nullable=False),
        sa.Column("new_decision_package_count", sa.Integer(), nullable=False),
        sa.Column("new_action_draft_count", sa.Integer(), nullable=False),
        sa.Column("diary_outcomes_closed_count", sa.Integer(), nullable=False),
        sa.Column("critical_event_count", sa.Integer(), nullable=False),
        sa.Column("alert_count", sa.Integer(), nullable=False),
        sa.Column("summary_nl", sa.Text(), nullable=False),
        sa.Column("help_nl", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
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
        sa.UniqueConstraint(
            "briefing_date", name="uq_daily_briefings_briefing_date"
        ),
    )

    op.create_table(
        "briefing_alerts",
        sa.Column("alert_id", sa.Text(), primary_key=True),
        sa.Column("briefing_id", sa.Text(), nullable=False),
        sa.Column("alert_kind", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("reference_kind", sa.Text(), nullable=True),
        sa.Column("reference_id", sa.Text(), nullable=True),
        sa.Column("title_nl", sa.Text(), nullable=False),
        sa.Column("body_nl", sa.Text(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
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
    )


def downgrade() -> None:
    op.drop_table("briefing_alerts")
    op.drop_table("daily_briefings")
