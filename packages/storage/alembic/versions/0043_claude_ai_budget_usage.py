"""claude AI budget usage audit table.

V1.1 §22.2 Slice 29 (real AI explanation provider). Tracks per-month
Anthropic Claude token cost so the provider can enforce the
``CLAUDE_AI_BUDGET_MONTHLY_EUR`` cap. Safety booleans hard-False; a
budget row never authorises an order.

Revision ID: 0043_claude_ai_budget_usage
Revises: 0042_prediction_diary_per_predictor
Create Date: 2026-05-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0043_claude_ai_budget_usage"
down_revision = "0042_prediction_diary_per_predictor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claude_ai_budget_usage",
        sa.Column("usage_id", sa.Text(), primary_key=True),
        sa.Column("budget_month", sa.Text(), nullable=False),  # YYYY-MM
        sa.Column("provider_code", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_units", sa.Integer(), nullable=False),
        sa.Column("cached_input_units", sa.Integer(), nullable=False),
        sa.Column("output_units", sa.Integer(), nullable=False),
        sa.Column("cost_eur", sa.Numeric(12, 6), nullable=False),
        sa.Column("call_kind", sa.Text(), nullable=False),  # explanation | ts_forecast
        sa.Column("explanation_nl", sa.Text(), nullable=True),
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
    op.create_index(
        "ix_claude_ai_budget_usage_month",
        "claude_ai_budget_usage",
        ["budget_month", "called_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_claude_ai_budget_usage_month",
        table_name="claude_ai_budget_usage",
    )
    op.drop_table("claude_ai_budget_usage")
