"""Add ``watchlist_preferences`` table — operator favorites + exclusions
(V1.2 §AU).

The CLAUDE.md doctrine §5 introduces a hybrid watchlist model with
three concurrent sources:

1. Universe-scan (autonomous, already wired through
   ``universe_scan_runs`` + ``asset_suggestions``).
2. Favorites list (operator-maintained): symbols the operator wants
   to monitor with live confidence even when they don't currently
   pass the gates. Surfaced in a dedicated dashboard block.
3. Exclusions list (operator-maintained): symbols the orchestrator
   must never propose, regardless of how strongly the gates favour
   them. Hard veto, operator-only.

The pre-existing ``watchlist_items`` table is reserved for the
cold-start seed + active monitoring pipeline (``source IN ('manual',
'cold_start_seed')``). Conflating the two would force the seed
machinery to learn about kind=excluded — a different lifecycle (the
operator can flip a symbol from favorite to excluded and back) and a
different consumer (the orchestrator candidate provider applies
exclusions before scoring). A dedicated table keeps both pipelines
independent and the migration trivially reversible.

Schema highlights:

* ``kind`` is locked to ``favorite`` / ``excluded`` so the
  orchestrator can index off it without parsing free-form strings.
* UNIQUE per ``(ibkr_account_ref, symbol, kind)`` so toggling a
  favorite twice is idempotent at the storage level.
* ``note`` is free-form — operator can jot down "tip from broer" or
  "te speculatief". The PDF audit-trail surfaces this verbatim.
* ``created_at`` is the only timestamp; an unwanted preference is
  deleted, never archived — keeps the table small and the
  orchestrator-side veto cheap.

Safety:
- No safe_for_* booleans; this table is configuration, not a
  decision-promoting record.
- No FK to asset_master_records: the operator may favourite a
  symbol before the universe scan has fetched its master record,
  and the exclusion must work even on a not-yet-master'd symbol.

Revision ID: 0073_watchlist_preferences
Revises: 0072_earnings_events
Create Date: 2026-06-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0073_watchlist_preferences"
down_revision = "0072_earnings_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_preferences",
        sa.Column("watchlist_preference_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_account_ref", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        # Locked vocabulary: favorite | excluded.
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('favorite', 'excluded')",
            name="ck_watchlist_preferences_kind",
        ),
        sa.CheckConstraint(
            "symbol <> ''",
            name="ck_watchlist_preferences_symbol_not_empty",
        ),
        sa.UniqueConstraint(
            "ibkr_account_ref", "symbol", "kind",
            name="uq_watchlist_preferences_account_symbol_kind",
        ),
    )
    op.create_index(
        "ix_watchlist_preferences_account_kind",
        "watchlist_preferences",
        ["ibkr_account_ref", "kind"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_watchlist_preferences_account_kind",
        table_name="watchlist_preferences",
    )
    op.drop_table("watchlist_preferences")
