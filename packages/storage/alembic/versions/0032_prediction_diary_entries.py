"""prediction diary entries durable storage.

Revision ID: 0032_prediction_diary_entries
Revises: 0031_action_draft_submissions_and_events
Create Date: 2026-05-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0032_prediction_diary_entries"
down_revision = "0031_action_draft_submissions_and_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_diary_entries",
        sa.Column("entry_id", sa.Text(), primary_key=True),
        sa.Column("suggestion_id", sa.Text(), nullable=False),
        sa.Column("forecast_id", sa.Text(), nullable=True),
        sa.Column("ibkr_conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_action_label", sa.Text(), nullable=False),
        sa.Column("issued_action_label_nl", sa.Text(), nullable=False),
        sa.Column("issued_confidence_label", sa.Text(), nullable=False),
        sa.Column("issued_horizon_days", sa.Integer(), nullable=False),
        sa.Column("issued_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("issued_p10_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("issued_p50_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("issued_p90_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("issued_prob_gain", sa.Numeric(10, 6), nullable=False),
        sa.Column("issued_prob_loss", sa.Numeric(10, 6), nullable=False),
        sa.Column("user_decision", sa.Text(), nullable=True),
        sa.Column("realized_price_1d", sa.Numeric(20, 6), nullable=True),
        sa.Column("realized_price_1w", sa.Numeric(20, 6), nullable=True),
        sa.Column("realized_price_1m", sa.Numeric(20, 6), nullable=True),
        sa.Column("realized_return_pct_1d", sa.Numeric(20, 6), nullable=True),
        sa.Column("realized_return_pct_1w", sa.Numeric(20, 6), nullable=True),
        sa.Column("realized_return_pct_1m", sa.Numeric(20, 6), nullable=True),
        sa.Column("outcome_label_1d", sa.Text(), nullable=True),
        sa.Column("outcome_label_1w", sa.Text(), nullable=True),
        sa.Column("outcome_label_1m", sa.Text(), nullable=True),
        sa.Column("outcome_explanation_nl", sa.Text(), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "safe_for_self_learning",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "safe_for_model_retraining",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.UniqueConstraint(
            "suggestion_id",
            name="uq_prediction_diary_entries_suggestion_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("prediction_diary_entries")
