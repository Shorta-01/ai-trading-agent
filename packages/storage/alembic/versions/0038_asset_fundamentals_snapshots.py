"""asset fundamentals snapshots for QVM factor scoring.

Revision ID: 0038_asset_fundamentals_snapshots
Revises: 0037_scheduler_runs
Create Date: 2026-06-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0038_asset_fundamentals_snapshots"
down_revision = "0037_scheduler_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_fundamentals_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_conid", sa.Text(), nullable=True),
        sa.Column("eodhd_symbol", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("sector", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("market_cap", sa.Numeric(24, 6), nullable=True),
        sa.Column("pe_ratio", sa.Numeric(20, 6), nullable=True),
        sa.Column("pb_ratio", sa.Numeric(20, 6), nullable=True),
        sa.Column("ev_ebitda", sa.Numeric(20, 6), nullable=True),
        sa.Column("roic_pct", sa.Numeric(20, 6), nullable=True),
        sa.Column("gross_margin_pct", sa.Numeric(20, 6), nullable=True),
        sa.Column("dividend_yield_pct", sa.Numeric(20, 6), nullable=True),
        sa.Column("return_6m_pct", sa.Numeric(20, 6), nullable=True),
        sa.Column("return_12m_pct", sa.Numeric(20, 6), nullable=True),
        sa.Column("raw_payload_hash", sa.Text(), nullable=False),
        sa.Column("provider_code", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "safe_for_orders",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "safe_for_action_drafts",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.UniqueConstraint(
            "eodhd_symbol",
            "fetched_at",
            name="uq_asset_fundamentals_snapshots_symbol_fetched_at",
        ),
    )


def downgrade() -> None:
    op.drop_table("asset_fundamentals_snapshots")
