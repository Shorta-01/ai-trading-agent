"""paper setup and audit foundation (paper-only, no runtime persistence wired yet)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_paper_setup_audit_foundation"
down_revision = None
branch_labels = None
depends_on = None


MONEY_NUMERIC = sa.Numeric(precision=20, scale=6)


def upgrade() -> None:
    op.create_table(
        "paper_portfolio_setups",
        sa.Column("setup_id", sa.Text(), nullable=False),
        sa.Column("portfolio_name", sa.Text(), nullable=False),
        sa.Column("base_currency", sa.Text(), nullable=False),
        sa.Column("starting_cash_amount", MONEY_NUMERIC, nullable=False),
        sa.Column("paper_only", sa.Boolean(), nullable=False),
        sa.Column("real_money_used", sa.Boolean(), nullable=False),
        sa.Column("broker_order_created", sa.Boolean(), nullable=False),
        sa.Column("live_trading_enabled", sa.Boolean(), nullable=False),
        sa.Column("user_confirmed_paper_only", sa.Boolean(), nullable=False),
        sa.Column("user_confirmed_no_real_money", sa.Boolean(), nullable=False),
        sa.Column("user_confirmed_no_broker_order", sa.Boolean(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint("base_currency = 'eur'", name="ck_paper_portfolio_setups_base_currency_eur"),
        sa.CheckConstraint("starting_cash_amount > 0", name="ck_paper_portfolio_setups_starting_cash_amount_gt_0"),
        sa.CheckConstraint("paper_only IS TRUE", name="ck_paper_portfolio_setups_paper_only_true"),
        sa.CheckConstraint("real_money_used IS FALSE", name="ck_paper_portfolio_setups_real_money_used_false"),
        sa.CheckConstraint("broker_order_created IS FALSE", name="ck_paper_portfolio_setups_broker_order_created_false"),
        sa.CheckConstraint("live_trading_enabled IS FALSE", name="ck_paper_portfolio_setups_live_trading_enabled_false"),
        sa.CheckConstraint("user_confirmed_paper_only IS TRUE", name="ck_paper_portfolio_setups_user_confirmed_paper_only_true"),
        sa.CheckConstraint("user_confirmed_no_real_money IS TRUE", name="ck_paper_portfolio_setups_user_confirmed_no_real_money_true"),
        sa.CheckConstraint("user_confirmed_no_broker_order IS TRUE", name="ck_paper_portfolio_setups_user_confirmed_no_broker_order_true"),
        sa.PrimaryKeyConstraint("setup_id"),
    )

    op.create_table(
        "paper_cash_accounts",
        sa.Column("paper_cash_account_id", sa.Text(), nullable=False),
        sa.Column("setup_id", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("initial_paper_cash_amount", MONEY_NUMERIC, nullable=False),
        sa.Column("paper_only", sa.Boolean(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint("currency = 'eur'", name="ck_paper_cash_accounts_currency_eur"),
        sa.CheckConstraint("initial_paper_cash_amount > 0", name="ck_paper_cash_accounts_initial_paper_cash_amount_gt_0"),
        sa.CheckConstraint("paper_only IS TRUE", name="ck_paper_cash_accounts_paper_only_true"),
        sa.ForeignKeyConstraint(["setup_id"], ["paper_portfolio_setups.setup_id"]),
        sa.PrimaryKeyConstraint("paper_cash_account_id"),
    )

    op.create_table(
        "audit_events",
        sa.Column("audit_event_id", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=True),
        sa.Column("entity_kind", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column("summary_nl", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("source_reference_ids_json", sa.JSON(), nullable=True),
        sa.Column("previous_hash", sa.Text(), nullable=True),
        sa.Column("event_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("event_type <> ''", name="ck_audit_events_event_type_not_empty"),
        sa.CheckConstraint("actor_type <> ''", name="ck_audit_events_actor_type_not_empty"),
        sa.CheckConstraint("entity_kind <> ''", name="ck_audit_events_entity_kind_not_empty"),
        sa.CheckConstraint("summary_nl <> ''", name="ck_audit_events_summary_nl_not_empty"),
        sa.PrimaryKeyConstraint("audit_event_id"),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("paper_cash_accounts")
    op.drop_table("paper_portfolio_setups")
