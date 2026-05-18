"""SQLAlchemy metadata and table definitions for storage foundation.

Paper setup and audit foundation only.
No runtime persistence wiring is enabled yet.
"""

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    Numeric,
    Table,
    Text,
)

MONEY_NUMERIC = Numeric(precision=20, scale=6)

metadata = MetaData()

paper_portfolio_setups = Table(
    "paper_portfolio_setups",
    metadata,
    Column("setup_id", Text, primary_key=True),
    Column("portfolio_name", Text, nullable=False),
    Column("base_currency", Text, nullable=False),
    Column("starting_cash_amount", MONEY_NUMERIC, nullable=False),
    Column("paper_only", Boolean, nullable=False),
    Column("real_money_used", Boolean, nullable=False),
    Column("broker_order_created", Boolean, nullable=False),
    Column("live_trading_enabled", Boolean, nullable=False),
    Column("user_confirmed_paper_only", Boolean, nullable=False),
    Column("user_confirmed_no_real_money", Boolean, nullable=False),
    Column("user_confirmed_no_broker_order", Boolean, nullable=False),
    Column("status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
    Column("explanation_nl", Text, nullable=False),
    CheckConstraint("base_currency = 'eur'", name="ck_paper_portfolio_setups_base_currency_eur"),
    CheckConstraint(
        "starting_cash_amount > 0",
        name="ck_paper_portfolio_setups_starting_cash_amount_gt_0",
    ),
    CheckConstraint("paper_only IS TRUE", name="ck_paper_portfolio_setups_paper_only_true"),
    CheckConstraint(
        "real_money_used IS FALSE",
        name="ck_paper_portfolio_setups_real_money_used_false",
    ),
    CheckConstraint(
        "broker_order_created IS FALSE",
        name="ck_paper_portfolio_setups_broker_order_created_false",
    ),
    CheckConstraint(
        "live_trading_enabled IS FALSE",
        name="ck_paper_portfolio_setups_live_trading_enabled_false",
    ),
    CheckConstraint(
        "user_confirmed_paper_only IS TRUE",
        name="ck_paper_portfolio_setups_user_confirmed_paper_only_true",
    ),
    CheckConstraint(
        "user_confirmed_no_real_money IS TRUE",
        name="ck_paper_portfolio_setups_user_confirmed_no_real_money_true",
    ),
    CheckConstraint(
        "user_confirmed_no_broker_order IS TRUE",
        name="ck_paper_portfolio_setups_user_confirmed_no_broker_order_true",
    ),
)

paper_cash_accounts = Table(
    "paper_cash_accounts",
    metadata,
    Column("paper_cash_account_id", Text, primary_key=True),
    Column("setup_id", Text, ForeignKey("paper_portfolio_setups.setup_id"), nullable=False),
    Column("currency", Text, nullable=False),
    Column("initial_paper_cash_amount", MONEY_NUMERIC, nullable=False),
    Column("paper_only", Boolean, nullable=False),
    Column("status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("explanation_nl", Text, nullable=False),
    CheckConstraint("currency = 'eur'", name="ck_paper_cash_accounts_currency_eur"),
    CheckConstraint(
        "initial_paper_cash_amount > 0",
        name="ck_paper_cash_accounts_initial_paper_cash_amount_gt_0",
    ),
    CheckConstraint("paper_only IS TRUE", name="ck_paper_cash_accounts_paper_only_true"),
)

audit_events = Table(
    "audit_events",
    metadata,
    Column("audit_event_id", Text, primary_key=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("event_type", Text, nullable=False),
    Column("actor_type", Text, nullable=False),
    Column("actor_id", Text, nullable=True),
    Column("entity_kind", Text, nullable=False),
    Column("entity_id", Text, nullable=True),
    Column("summary_nl", Text, nullable=False),
    Column("payload_json", JSON, nullable=True),
    Column("source_reference_ids_json", JSON, nullable=True),
    Column("previous_hash", Text, nullable=True),
    Column("event_hash", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("event_type <> ''", name="ck_audit_events_event_type_not_empty"),
    CheckConstraint("actor_type <> ''", name="ck_audit_events_actor_type_not_empty"),
    CheckConstraint("entity_kind <> ''", name="ck_audit_events_entity_kind_not_empty"),
    CheckConstraint("summary_nl <> ''", name="ck_audit_events_summary_nl_not_empty"),
)
