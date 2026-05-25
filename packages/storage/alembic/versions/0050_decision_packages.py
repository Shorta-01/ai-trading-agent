"""Task 132: Decision Packages.

Adds the ``decision_packages`` table — an append-only, audit-traceable
container that wraps a single forecast for a single (ibkr_account_id,
conid) at a single moment in time, along with every snapshot needed
to make the suggested action either approvable or refutable.

Composed only when the underlying forecast label is NOT ``Geblokkeerd``
(see Task 132 product lock §2 and the CHECK constraint on
``suggested_action_label``). Hash-chained per (account, conid) via
``previous_package_hash`` → tamper-evident.

Safety booleans (``safe_for_action_drafts``, ``safe_for_orders``) are
hard-False via CHECK constraint. They only flip in future tasks when
the Action Center + approval workflows ship with their own product
locks.

Revision ID: 0050_decision_packages
Revises: 0049_forecasts_and_calibration_diary
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0050_decision_packages"
down_revision = "0049_forecasts_and_calibration_diary"
branch_labels = None
depends_on = None

_PRICE = sa.Numeric(precision=20, scale=8)
_RETURN = sa.Numeric(precision=20, scale=10)
_PROB = sa.Numeric(precision=8, scale=6)
_VOL = sa.Numeric(precision=10, scale=8)


def upgrade() -> None:
    op.create_table(
        "decision_packages",
        sa.Column("decision_package_id", sa.Text(), primary_key=True),
        sa.Column("forecast_run_id", sa.Text(), nullable=False),
        sa.Column("composed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ibkr_account_id", sa.Text(), nullable=False),
        sa.Column("conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("currency_local", sa.Text(), nullable=False),
        sa.Column("asset_class", sa.Text(), nullable=True),
        sa.Column("user_holds_position", sa.Boolean(), nullable=False),
        sa.Column("held_quantity", _PRICE, nullable=True),
        sa.Column("held_avg_cost_local", _PRICE, nullable=True),
        sa.Column("current_price_local", _PRICE, nullable=False),
        sa.Column("current_price_eur", _PRICE, nullable=False),
        sa.Column(
            "as_of_market_data_ts", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("freshness_state", sa.Text(), nullable=False),
        sa.Column("data_age_trading_days", sa.Integer(), nullable=False),
        sa.Column("forecast_method", sa.Text(), nullable=False),
        sa.Column("p10_log_return", _RETURN, nullable=False),
        sa.Column("p50_log_return", _RETURN, nullable=False),
        sa.Column("p90_log_return", _RETURN, nullable=False),
        sa.Column("p10_price_eur", _PRICE, nullable=False),
        sa.Column("p50_price_eur", _PRICE, nullable=False),
        sa.Column("p90_price_eur", _PRICE, nullable=False),
        sa.Column("prob_positive", _PROB, nullable=False),
        sa.Column("prob_loss_gt_5pct", _PROB, nullable=False),
        sa.Column("expected_volatility_annualized", _VOL, nullable=False),
        sa.Column("forecast_confidence_level", sa.Text(), nullable=False),
        sa.Column("suggested_action_label", sa.Text(), nullable=False),
        sa.Column("block_reason", sa.Text(), nullable=True),
        sa.Column("gate_outcomes_json", sa.JSON(), nullable=False),
        sa.Column("evidence_references_json", sa.JSON(), nullable=False),
        sa.Column(
            "deterministic_dutch_explanation", sa.Text(), nullable=False
        ),
        sa.Column("audit_trail_hash", sa.Text(), nullable=False),
        sa.Column("previous_package_hash", sa.Text(), nullable=True),
        sa.Column(
            "safe_for_action_drafts",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "safe_for_orders",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.CheckConstraint(
            "freshness_state IN ('fresh', 'stale', 'unavailable')",
            name="ck_decision_packages_freshness_state",
        ),
        sa.CheckConstraint(
            "forecast_method IN ('historical_bootstrap_v1')",
            name="ck_decision_packages_forecast_method",
        ),
        sa.CheckConstraint(
            "forecast_confidence_level IN ('Laag', 'Gemiddeld', 'Hoog')",
            name="ck_decision_packages_forecast_confidence_level",
        ),
        # 'Geblokkeerd' is explicitly excluded — Task 132 product lock §2.
        sa.CheckConstraint(
            "suggested_action_label IN ('Kopen', 'Verminderen', "
            "'Verkopen', 'Houden', 'Bekijken')",
            name="ck_decision_packages_suggested_action_label",
        ),
        sa.CheckConstraint(
            "prob_positive >= 0 AND prob_positive <= 1",
            name="ck_decision_packages_prob_positive_range",
        ),
        sa.CheckConstraint(
            "prob_loss_gt_5pct >= 0 AND prob_loss_gt_5pct <= 1",
            name="ck_decision_packages_prob_loss_range",
        ),
        sa.CheckConstraint(
            "data_age_trading_days >= 0",
            name="ck_decision_packages_data_age_nonneg",
        ),
        sa.CheckConstraint(
            "safe_for_action_drafts = FALSE",
            name="ck_decision_packages_safe_action_drafts_false",
        ),
        sa.CheckConstraint(
            "safe_for_orders = FALSE",
            name="ck_decision_packages_safe_orders_false",
        ),
    )
    op.create_index(
        "ix_decision_packages_account_conid_composed",
        "decision_packages",
        [
            "ibkr_account_id",
            "conid",
            sa.text("composed_at DESC"),
        ],
    )
    op.create_index(
        "ix_decision_packages_forecast_run_id",
        "decision_packages",
        ["forecast_run_id"],
    )
    op.create_index(
        "ix_decision_packages_audit_hash",
        "decision_packages",
        ["audit_trail_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_decision_packages_audit_hash", table_name="decision_packages"
    )
    op.drop_index(
        "ix_decision_packages_forecast_run_id",
        table_name="decision_packages",
    )
    op.drop_index(
        "ix_decision_packages_account_conid_composed",
        table_name="decision_packages",
    )
    op.drop_table("decision_packages")
