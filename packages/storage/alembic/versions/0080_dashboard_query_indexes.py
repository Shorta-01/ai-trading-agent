"""Add covering indexes for dashboard queries — P2-6 (V1.2 §CG).

GAPS.md P2-6 — de storage-audit identificeerde dat veel
dashboard-queries scannen op kolommen zonder index (``status``,
``created_at``, ``asset_symbol``). Op kleine V1-data niet
merkbaar, maar bij groei (>10k action_drafts, >50k audit-events)
loopt het dashboard merkbaar trager.

Deze migratie voegt zeven defensieve indexes toe op de meest
gequerysde tabellen. Bewust conservatief gekozen — alleen
single-column of (account, kolom) composiet, om writes niet
nodeloos te belasten:

* ``asset_action_drafts.status`` — stage-filter op /ibkr-acties +
  dashboard Stage-2/3 widgets (V1.2 §BO)
* ``asset_suggestions.status`` — orchestrator-verdicts
  filtering
* ``orchestrator_scoring_verdicts.generated_at`` — historiek-
  paginering
* ``system_events.created_at`` — /systeemmeldingen audit-page
* ``audit_events.occurred_at`` — algemene audit-trail
* ``dividend_events.created_at`` — manueel dividenden-register
  (V1.2 §BA)
* ``earnings_events.fetched_at`` — earnings-calendar
  freshness check

Doctrine-borging: alleen leesperformance — geen schema-wijziging,
geen kolom-toevoegingen, geen safe_for_* aanpassingen. Werkt
incrementeel op zowel een leeg als een gevuld systeem zonder
locks (Postgres CREATE INDEX is read-blocking, niet write-
blocking; voor V1 paper-volumes irrelevant).

Revision ID: 0080_dashboard_query_indexes
Revises: 0079_macro_index_snapshots
Create Date: 2026-06-14
"""

from alembic import op

revision = "0080_dashboard_query_indexes"
down_revision = "0079_macro_index_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_asset_action_drafts_status",
        "asset_action_drafts",
        ["status"],
    )
    op.create_index(
        "ix_asset_suggestions_status",
        "asset_suggestions",
        ["status"],
    )
    op.create_index(
        "ix_orchestrator_scoring_verdicts_generated_at",
        "orchestrator_scoring_verdicts",
        ["generated_at"],
    )
    op.create_index(
        "ix_system_events_created_at",
        "system_events",
        ["created_at"],
    )
    op.create_index(
        "ix_audit_events_occurred_at",
        "audit_events",
        ["occurred_at"],
    )
    op.create_index(
        "ix_dividend_events_created_at",
        "dividend_events",
        ["created_at"],
    )
    op.create_index(
        "ix_earnings_events_fetched_at",
        "earnings_events",
        ["fetched_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_earnings_events_fetched_at",
        table_name="earnings_events",
    )
    op.drop_index(
        "ix_dividend_events_created_at",
        table_name="dividend_events",
    )
    op.drop_index(
        "ix_audit_events_occurred_at",
        table_name="audit_events",
    )
    op.drop_index(
        "ix_system_events_created_at",
        table_name="system_events",
    )
    op.drop_index(
        "ix_orchestrator_scoring_verdicts_generated_at",
        table_name="orchestrator_scoring_verdicts",
    )
    op.drop_index(
        "ix_asset_suggestions_status",
        table_name="asset_suggestions",
    )
    op.drop_index(
        "ix_asset_action_drafts_status",
        table_name="asset_action_drafts",
    )
