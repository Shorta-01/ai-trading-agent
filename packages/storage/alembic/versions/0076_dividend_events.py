"""Add ``dividend_events`` table — operator-tracked dividends
(V1.2 §BA / CLAUDE.md §12 follow-up).

V1 heeft geen live dividend-feed (geen broker-sync van DRIPs of cash
dividenden). De /belasting pagina vraagt wel een sectie "ontvangen
dividenden" voor de Belgische roerende voorheffing-regularisatie.

Tot een feed beschikbaar is, slaat de operator dividenden manueel
op via een /dividenden endpoint. Per dividend:

* Symbol + ISIN (operator-input)
* Pay-date
* Bruto bedrag in lokale munt
* Bronbelasting ingehouden (standaard verdrag-tarief: US 15 %, NL 15 %,
  FR 12,8 %, BE 0 % — operator kan overrulen)
* Netto ontvangen (afgeleid maar opgeslagen voor audit-stabiliteit)

De Belgische 30 % roerende voorheffing-regularisatie wordt
client-side berekend: netto × (1 - 0.30) = effectief netto.

Safe_for_* booleans niet nodig: dividend-events zijn rapportage,
geen actie-promoter.

Revision ID: 0076_dividend_events
Revises: 0075_runtime_config_profit_target
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0076_dividend_events"
down_revision = "0075_runtime_config_profit_target"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dividend_events",
        sa.Column("dividend_event_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_account_ref", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("isin", sa.Text(), nullable=True),
        sa.Column("pay_date", sa.Date(), nullable=False),
        sa.Column("currency_local", sa.Text(), nullable=False),
        sa.Column("gross_local", sa.Numeric(20, 8), nullable=False),
        # Bronbelasting-tarief als percentage (15 = 15 %). Operator
        # mag het verdrag-tarief overrulen.
        sa.Column("withholding_pct", sa.Numeric(20, 8), nullable=False),
        sa.Column("withholding_local", sa.Numeric(20, 8), nullable=False),
        sa.Column("net_local", sa.Numeric(20, 8), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "gross_local >= 0",
            name="ck_dividend_events_gross_non_negative",
        ),
        sa.CheckConstraint(
            "withholding_pct >= 0 AND withholding_pct <= 100",
            name="ck_dividend_events_withholding_pct_range",
        ),
        sa.CheckConstraint(
            "symbol <> ''",
            name="ck_dividend_events_symbol_not_empty",
        ),
    )
    op.create_index(
        "ix_dividend_events_account_date",
        "dividend_events",
        ["ibkr_account_ref", "pay_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dividend_events_account_date", table_name="dividend_events"
    )
    op.drop_table("dividend_events")
