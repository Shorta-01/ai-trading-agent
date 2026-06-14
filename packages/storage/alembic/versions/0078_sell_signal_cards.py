"""Add ``sell_signal_cards`` table — SELL-suggestie kaartjes voor de
SELL-loop sweep (V1.2 §BF / CLAUDE.md §6.2 + §6.3).

Twee signaal-soorten landen in dezelfde tabel:

* ``take_profit`` (CLAUDE.md §6.3) — intraday check tegen de +4%
  target. ``action='suggest_sell'`` zodra de positie het target
  raakt; ``action='hold'`` daarvoor.
* ``hold_review`` (CLAUDE.md §6.2) — maandelijkse 6m+ combo-trigger
  (forecast verzwakt EN positie in verlies). ``action='suggest_sell'``
  alleen als beide condities waar zijn.

Eén ACTIVE kaartje per ``(ibkr_account_ref, symbol, signal_kind)``
— de sweep upsert op die unique key. ``dismissed_at`` wordt door de
operator gezet via de UI; volgende sweep behoudt de dismissal voor
*dezelfde* signaal-staat. Wanneer het signaal materieel verandert
(b.v. ``hold`` → ``suggest_sell`` na een dip onder de loss-floor)
wordt ``dismissed_at`` automatisch gewist zodat de operator het
hernieuwde signaal te zien krijgt.

CLAUDE.md §2 fundamenteel principe: deze kaartjes zijn ADVIES. De
software stuurt NOOIT een order zonder operator-klik. ``safe_for_*``
flags blijven op False — een toekomstige UI-laag mag deze kaartjes
gebruiken om een SELL action-draft voor te bereiden maar nooit
direct submitten.

CLAUDE.md §11 fundamenteel principe: SELL-monitoring blijft draaien
tijdens software-pauze (de operator wil geen +4% hits missen). De
sweep checkt expliciet GEEN pauze-flag.

Revision ID: 0078_sell_signal_cards
Revises: 0077_monthly_report_archive
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0078_sell_signal_cards"
down_revision = "0077_monthly_report_archive"
branch_labels = None
depends_on = None


_MONEY_NUMERIC = sa.Numeric(precision=20, scale=6)


def upgrade() -> None:
    op.create_table(
        "sell_signal_cards",
        sa.Column("card_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_account_ref", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("signal_kind", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entry_price", _MONEY_NUMERIC, nullable=False),
        sa.Column("current_price", _MONEY_NUMERIC, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("current_pct_return", _MONEY_NUMERIC, nullable=False),
        sa.Column("target_pct", _MONEY_NUMERIC, nullable=True),
        sa.Column("target_reached", sa.Boolean(), nullable=True),
        sa.Column("days_held", sa.Integer(), nullable=True),
        sa.Column("forecast_id", sa.Text(), nullable=True),
        sa.Column("forecaster_above_target", sa.Boolean(), nullable=True),
        sa.Column("position_in_loss", sa.Boolean(), nullable=True),
        sa.Column("short_term_p50", _MONEY_NUMERIC, nullable=True),
        sa.Column("short_term_horizon_days", sa.Integer(), nullable=True),
        sa.Column("short_term_prob_above_pct", _MONEY_NUMERIC, nullable=True),
        sa.Column("expected_net_proceeds_eur", _MONEY_NUMERIC, nullable=True),
        sa.Column("headline_nl", sa.Text(), nullable=False),
        sa.Column("detail_nl", sa.Text(), nullable=False),
        sa.Column("first_generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_reason", sa.Text(), nullable=True),
        sa.Column(
            "safe_for_action_drafts",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.CheckConstraint(
            "signal_kind IN ('take_profit', 'hold_review')",
            name="ck_sell_signal_cards_signal_kind",
        ),
        sa.CheckConstraint(
            "action IN ('hold', 'suggest_sell')",
            name="ck_sell_signal_cards_action",
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_sell_signal_cards_quantity_positive",
        ),
        sa.CheckConstraint(
            "entry_price > 0",
            name="ck_sell_signal_cards_entry_price_positive",
        ),
        sa.CheckConstraint(
            "current_price > 0",
            name="ck_sell_signal_cards_current_price_positive",
        ),
        sa.CheckConstraint(
            "symbol <> ''",
            name="ck_sell_signal_cards_symbol_not_empty",
        ),
        sa.CheckConstraint(
            "headline_nl <> ''",
            name="ck_sell_signal_cards_headline_not_empty",
        ),
        sa.UniqueConstraint(
            "ibkr_account_ref",
            "symbol",
            "signal_kind",
            name="uq_sell_signal_cards_account_symbol_kind",
        ),
    )
    op.create_index(
        "ix_sell_signal_cards_active",
        "sell_signal_cards",
        ["ibkr_account_ref", "action", "dismissed_at"],
    )
    op.create_index(
        "ix_sell_signal_cards_last_evaluated_at",
        "sell_signal_cards",
        ["last_evaluated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sell_signal_cards_last_evaluated_at",
        table_name="sell_signal_cards",
    )
    op.drop_index(
        "ix_sell_signal_cards_active",
        table_name="sell_signal_cards",
    )
    op.drop_table("sell_signal_cards")
