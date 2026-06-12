"""Add ``earnings_events`` table — upcoming earnings calendar feed
(V1.2 §AI).

Replaces the hardcoded ``next_earnings_date=None`` placeholder the
orchestrator candidate provider has been carrying since V1.2 §M. The
profit-harvest doctrine's earnings-window gate (V1.2 §R) refuses new
BUY suggestions inside a configurable window before earnings, but
without a real calendar feed every candidate currently looks
"earnings-clean". This table is the storage shape the EODHD adapter
+ orchestrator hookup write/read against.

Decoupling rationale:

* One row per ``(symbol, event_date)`` so the same symbol can carry
  multiple upcoming events without overwriting prior ones — useful
  for the rare case where a provider returns both an interim report
  and an annual.
* ``status`` distinguishes ``confirmed`` vs ``estimated`` so the gate
  can pick a stricter threshold for estimated dates when needed.
* ``source`` and ``fetched_at`` are persisted so the audit chain
  knows which provider supplied the date and how stale it is — V1
  uses EODHD, V2 may add SEC EDGAR for US issuers.
* ``raw_json`` keeps the provider response intact so future fields
  (eps-estimate, eps-actual, revenue-estimate) can be surfaced
  without migrating again.

Revision ID: 0072_earnings_events
Revises: 0071_orchestrator_scoring_verdicts
Create Date: 2026-06-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0072_earnings_events"
down_revision = "0071_orchestrator_scoring_verdicts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "earnings_events",
        sa.Column("earnings_event_id", sa.Text(), primary_key=True),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("ibkr_conid", sa.Text(), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=False),
        # Locked vocabulary: confirmed | estimated | past.
        sa.Column("status", sa.Text(), nullable=False),
        # Provider code (e.g. "eodhd"). Free-form so future providers
        # don't need a migration to register themselves.
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        # Provider payload kept intact for future enrichment.
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "status IN ('confirmed', 'estimated', 'past')",
            name="ck_earnings_events_status",
        ),
        # One event per (symbol, date) — re-fetches upsert instead
        # of duplicating.
        sa.UniqueConstraint(
            "symbol", "event_date",
            name="uq_earnings_events_symbol_date",
        ),
    )
    op.create_index(
        "ix_earnings_events_symbol_date",
        "earnings_events",
        ["symbol", "event_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_earnings_events_symbol_date", table_name="earnings_events")
    op.drop_table("earnings_events")
