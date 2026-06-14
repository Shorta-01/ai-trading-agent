"""Add ``macro_index_snapshots`` table — VIX + breed-marktindex bars
(V1.2 §BE / post-§BC follow-up #1).

CLAUDE.md §7.2 maakt van de macro-gate een informatieve waarschuwing
maar de orchestrator-scoring-leg leest hem nog steeds: een verkeerd
ingestelde VIX = 15 maakt elke marktdaling onzichtbaar. Tot deze
migratie was er geen storage-plek voor *historische* index- en VIX-
bars op één symbool — ``market_data_bars`` zit aan ``ibkr_conid``
vast en VIX/SPX hebben geen IBKR-conid in onze setup.

Schema-keuzes:

* Eén tabel voor meerdere series, geïdentificeerd via
  ``series_code`` (free-form). Locked codes voor V1: ``vix`` (CBOE
  VIX) en ``spx`` (S&P 500 close). Toekomstige codes (Euro STOXX,
  Bel-20) kunnen toegevoegd worden zonder migratie.
* Eén rij per ``(series_code, bar_date)``. Refetch upsert in plaats
  van duplicate.
* ``raw_payload`` is een dict zodat we de provider-respons
  (open/high/low/volume) kunnen bewaren voor toekomstige indicatoren
  zonder migratie.
* ``provider`` documenteert de bron; in V1 alleen ``eodhd``.

Geen ``safe_for_*`` boolean: de tabel is feed-data, geen actie-
promoter. De macro-regime gate beslist zelf wat hij met de waarden
doet.

Revision ID: 0079_macro_index_snapshots
Revises: 0078_sell_signal_cards
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0079_macro_index_snapshots"
down_revision = "0078_sell_signal_cards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "macro_index_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("series_code", sa.Text(), nullable=False),
        sa.Column("bar_date", sa.Date(), nullable=False),
        sa.Column("close_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "series_code <> ''",
            name="ck_macro_index_snapshots_series_not_empty",
        ),
        sa.CheckConstraint(
            "close_value > 0",
            name="ck_macro_index_snapshots_close_positive",
        ),
        sa.UniqueConstraint(
            "series_code", "bar_date",
            name="uq_macro_index_snapshots_series_date",
        ),
    )
    op.create_index(
        "ix_macro_index_snapshots_series_date",
        "macro_index_snapshots",
        ["series_code", "bar_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_macro_index_snapshots_series_date",
        table_name="macro_index_snapshots",
    )
    op.drop_table("macro_index_snapshots")
