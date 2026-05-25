"""prediction diary per-predictor contributions.

V1.1 §22.5 Slice 26 (feedback loop). Adds a child table that records
one row per (diary_entry_id, model_code) so the auto-weighted
ensemble strategy can compute a rolling per-predictor Brier score.
Safety booleans hard-False; the row never authorises an order.

Revision ID: 0042_prediction_diary_per_predictor
Revises: 0041_predictor_backtest_runs
Create Date: 2026-05-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0042_prediction_diary_per_predictor"
down_revision = "0041_predictor_backtest_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_diary_predictor_contributions",
        sa.Column("contribution_id", sa.Text(), primary_key=True),
        sa.Column("diary_entry_id", sa.Text(), nullable=False),
        sa.Column("model_code", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("predicted_return_pct", sa.Numeric(20, 6), nullable=False),
        sa.Column("predicted_prob_gain", sa.Numeric(10, 6), nullable=False),
        sa.Column("predicted_direction", sa.Text(), nullable=False),
        sa.Column("realised_return_pct", sa.Numeric(20, 6), nullable=True),
        sa.Column("realised_direction", sa.Text(), nullable=True),
        sa.Column("outcome_label", sa.Text(), nullable=True),
        sa.Column("brier_score", sa.Numeric(12, 6), nullable=True),
        sa.Column("return_spread_pct", sa.Numeric(20, 6), nullable=True),
        sa.Column("explanation_nl", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
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
        "ix_prediction_diary_predictor_contributions_entry",
        "prediction_diary_predictor_contributions",
        ["diary_entry_id"],
    )
    op.create_index(
        "ix_prediction_diary_predictor_contributions_model",
        "prediction_diary_predictor_contributions",
        ["model_code", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prediction_diary_predictor_contributions_model",
        table_name="prediction_diary_predictor_contributions",
    )
    op.drop_index(
        "ix_prediction_diary_predictor_contributions_entry",
        table_name="prediction_diary_predictor_contributions",
    )
    op.drop_table("prediction_diary_predictor_contributions")
