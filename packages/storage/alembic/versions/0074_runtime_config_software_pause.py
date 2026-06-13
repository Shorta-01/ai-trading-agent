"""Add ``software_paused`` + ``software_paused_at`` to ``runtime_config``
(V1.2 §AY / CLAUDE.md §11).

CLAUDE.md §11 voorziet één pauze-knop op het dashboard. Bij activatie:

* Morning chain stopt (geen nieuwe BUY-voorstellen).
* SELL-monitoring blijft draaien (operator wil geen +4 % hit missen).
* Oranje statusbalk bovenaan dashboard met "Software gepauzeerd
  sinds DD/MM/YYYY".

De gepauzeerd-state is per definitie globaal: er is één
``runtime_config`` row (``config_id="default"``) waar deze flag bij
hoort. Twee kolommen volstaan:

* ``software_paused`` (bool, default False) — de huidige toestand.
* ``software_paused_at`` (timestamp, nullable) — wanneer de operator
  de pauze ingedrukt heeft. Een nullable timestamp houdt de oorzaak
  / audit-trail simpel: bij ``hervat`` zet de API het terug op
  NULL en flipt de bool naar False.

Een aparte ``paused_log`` tabel zou de audit-trail beter
ondersteunen maar is in V1 overkill — de operator pauzeert dit niet
vaak en als hij geschiedenis nodig heeft is dat een feature voor
later. Eerste-versie keuze: KISS.

Revision ID: 0074_runtime_config_software_pause
Revises: 0073_watchlist_preferences
Create Date: 2026-06-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0074_runtime_config_software_pause"
down_revision = "0073_watchlist_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "runtime_config",
        sa.Column(
            "software_paused",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "runtime_config",
        sa.Column(
            "software_paused_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("runtime_config", "software_paused_at")
    op.drop_column("runtime_config", "software_paused")
