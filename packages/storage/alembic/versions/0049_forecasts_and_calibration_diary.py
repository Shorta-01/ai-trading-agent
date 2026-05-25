"""Task 130: probabilistic forecast + calibration diary.

Adds two tables for the baseline historical-bootstrap forecast:

* ``forecasts`` — append-only one-row-per-fire. Locked CHECK on
  ``method`` (only ``historical_bootstrap_v1`` for V1.1.0),
  ``label`` (the six locked Dutch values), ``confidence_level``
  (``Laag``/``Gemiddeld``/``Hoog``). UNIQUE on
  ``(conid, generated_at)`` enforces fetch-idempotency-style
  deduplication. Index on ``(conid, generated_at DESC)`` for the
  latest-per-conid read path.
* ``calibration_diary`` — append-only one-row-per-expired-forecast.
  PRIMARY KEY = ``forecast_run_id`` (1:1 with the forecast) so a
  re-evaluation can't double-write. Locked CHECK on ``hit_status``.

Revision ID: 0049_forecasts_and_calibration_diary
Revises: 0048_market_data_eod_and_fx_runtime
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0049_forecasts_and_calibration_diary"
down_revision = "0048_market_data_eod_and_fx_runtime"
branch_labels = None
depends_on = None

_PRICE = sa.Numeric(precision=20, scale=8)
_RETURN = sa.Numeric(precision=20, scale=10)
_PROB = sa.Numeric(precision=8, scale=6)
_VOL = sa.Numeric(precision=10, scale=8)


def upgrade() -> None:
    op.create_table(
        "forecasts",
        sa.Column("forecast_run_id", sa.Text(), primary_key=True),
        sa.Column("conid", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "generated_by_scheduled_run_id", sa.Text(), nullable=False
        ),
        sa.Column("horizon_trading_days", sa.Integer(), nullable=False),
        sa.Column(
            "forecast_valid_until", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("history_window_days", sa.Integer(), nullable=False),
        sa.Column("history_closes_count", sa.Integer(), nullable=False),
        sa.Column("current_price_local", _PRICE, nullable=False),
        sa.Column("currency_local", sa.Text(), nullable=False),
        sa.Column("p10_log_return", _RETURN, nullable=False),
        sa.Column("p50_log_return", _RETURN, nullable=False),
        sa.Column("p90_log_return", _RETURN, nullable=False),
        sa.Column("prob_positive", _PROB, nullable=False),
        sa.Column("prob_loss_gt_5pct", _PROB, nullable=False),
        sa.Column("expected_volatility_annualized", _VOL, nullable=False),
        sa.Column("confidence_level", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("block_reason", sa.Text(), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "conid", "generated_at", name="uq_forecasts_conid_generated_at"
        ),
        sa.CheckConstraint(
            "horizon_trading_days > 0", name="ck_forecasts_horizon_positive"
        ),
        sa.CheckConstraint(
            "method IN ('historical_bootstrap_v1')",
            name="ck_forecasts_method",
        ),
        sa.CheckConstraint(
            "prob_positive >= 0 AND prob_positive <= 1",
            name="ck_forecasts_prob_positive_range",
        ),
        sa.CheckConstraint(
            "prob_loss_gt_5pct >= 0 AND prob_loss_gt_5pct <= 1",
            name="ck_forecasts_prob_loss_range",
        ),
        sa.CheckConstraint(
            "confidence_level IN ('Laag', 'Gemiddeld', 'Hoog')",
            name="ck_forecasts_confidence",
        ),
        sa.CheckConstraint(
            "label IN ('Kopen', 'Verminderen', 'Verkopen', 'Houden',"
            " 'Bekijken', 'Geblokkeerd')",
            name="ck_forecasts_label",
        ),
    )
    op.create_index(
        "ix_forecasts_conid_generated_at",
        "forecasts",
        ["conid", sa.text("generated_at DESC")],
    )

    op.create_table(
        "calibration_diary",
        sa.Column("forecast_run_id", sa.Text(), primary_key=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("realized_log_return", _RETURN, nullable=False),
        sa.Column("hit_status", sa.Text(), nullable=False),
        sa.Column("realized_close_price", _PRICE, nullable=False),
        sa.CheckConstraint(
            "hit_status IN ('realized_within_p10_p90', 'realized_outside_band',"
            " 'realized_above_p90', 'realized_below_p10')",
            name="ck_calibration_diary_hit_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("calibration_diary")
    op.drop_index("ix_forecasts_conid_generated_at", table_name="forecasts")
    op.drop_table("forecasts")
