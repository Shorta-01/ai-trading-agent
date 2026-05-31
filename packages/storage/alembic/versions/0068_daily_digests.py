"""Add ``daily_digests`` table — one end-of-day digest per (account, date).

Backs the end-of-day digest the worker computes on every ``market_close``
fire. Stores everything the operator needs to read tomorrow morning's
"what happened yesterday" summary: NAV delta, top winners/losers,
suggestion counts by action label, and action-draft activity counts.

Why a JSON-blob design rather than fully normalised rows:
- The digest is read whole, never queried by sub-field, so a wide row
  is cheaper than 5 child tables.
- The shape evolves with new metrics (we'll add per-predictor accuracy
  later) without per-field migrations.

Revision ID: 0068_daily_digests
Revises: 0067_runtime_config_market_aware_scheduler
Create Date: 2026-05-31
"""

import sqlalchemy as sa
from alembic import op

revision = "0068_daily_digests"
down_revision = "0067_runtime_config_market_aware_scheduler"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_digests",
        sa.Column("digest_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_account_ref", sa.Text(), nullable=False),
        sa.Column("market_code", sa.Text(), nullable=False),
        sa.Column("briefing_date", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nav_summary_json", sa.JSON(), nullable=False),
        sa.Column("positions_summary_json", sa.JSON(), nullable=False),
        sa.Column("suggestions_summary_json", sa.JSON(), nullable=False),
        sa.Column("action_drafts_summary_json", sa.JSON(), nullable=False),
        sa.Column("alerts_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "ibkr_account_ref",
            "market_code",
            "briefing_date",
            name="uq_daily_digest_per_account_market_day",
        ),
    )


def downgrade() -> None:
    op.drop_table("daily_digests")
