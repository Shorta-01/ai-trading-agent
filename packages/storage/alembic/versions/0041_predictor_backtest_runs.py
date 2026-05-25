"""predictor backtest runs audit table.

V1.1 §22 Slice 24 (predictor refactor base). Persists one row per
backtest invocation. Slice 25 wires the walk-forward harness; Slice 26
reads back into the auto-weighted ensemble strategy. Safety booleans
hard-False; a backtest result never authorises an order.

Revision ID: 0041_predictor_backtest_runs
Revises: 0040_action_draft_order_vocabulary
Create Date: 2026-05-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0041_predictor_backtest_runs"
down_revision = "0040_action_draft_order_vocabulary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "predictor_backtest_runs",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("model_code", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("asset_symbol", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("bars_used", sa.Integer(), nullable=False),
        sa.Column("brier_score", sa.Numeric(12, 6), nullable=True),
        sa.Column("hit_rate", sa.Numeric(8, 6), nullable=True),
        sa.Column("sharpe_ratio", sa.Numeric(12, 6), nullable=True),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
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
        "ix_predictor_backtest_runs_model_code",
        "predictor_backtest_runs",
        ["model_code", "asset_symbol", "started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_predictor_backtest_runs_model_code",
        table_name="predictor_backtest_runs",
    )
    op.drop_table("predictor_backtest_runs")
