"""Task T-045 §2: portfolio NAV history for the drawdown circuit-breaker.

Adds ``ibkr_nav_snapshots`` — a per-account time series of the IBKR
NetLiquidationValue. The submission drawdown gate reads this to compute the
decline-from-peak over its lookback windows. Unlike the cash-snapshot path,
every row carries ``ibkr_account_id`` so the per-account series is queryable.

Revision ID: 0054_ibkr_nav_snapshots
Revises: 0053_reconciliation_audit_and_manual_review
Create Date: 2026-05-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0054_ibkr_nav_snapshots"
down_revision = "0053_reconciliation_audit_and_manual_review"
branch_labels = None
depends_on = None

_MONEY = sa.Numeric(precision=20, scale=6)


def upgrade() -> None:
    op.create_table(
        "ibkr_nav_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_account_id", sa.Text(), nullable=False),
        sa.Column("base_currency", sa.Text(), nullable=False),
        sa.Column("nav_value", _MONEY, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "nav_value > 0", name="ck_ibkr_nav_snapshots_nav_positive"
        ),
    )
    op.create_index(
        "ix_ibkr_nav_snapshots_account_time",
        "ibkr_nav_snapshots",
        ["ibkr_account_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ibkr_nav_snapshots_account_time", table_name="ibkr_nav_snapshots"
    )
    op.drop_table("ibkr_nav_snapshots")
