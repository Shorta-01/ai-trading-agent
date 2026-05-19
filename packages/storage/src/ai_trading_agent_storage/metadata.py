"""SQLAlchemy metadata and table definitions for storage foundation.

Paper setup, audit, and broker sync foundation slice 1 only.
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
from sqlalchemy import (
    false as sa_false,
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



system_events = Table(
    "system_events",
    metadata,
    Column("system_event_id", Text, primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("severity", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("source_service", Text, nullable=False),
    Column("source_component", Text, nullable=False),
    Column("event_code", Text, nullable=False),
    Column("title_nl", Text, nullable=False),
    Column("message_nl", Text, nullable=False),
    Column("help_nl", Text, nullable=False),
    Column("technical_summary", Text, nullable=True),
    Column("redacted_details_json", JSON, nullable=True),
    Column("stack_trace_redacted", Text, nullable=True),
    Column("related_entity_type", Text, nullable=True),
    Column("related_entity_id", Text, nullable=True),
    Column("blocks_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("blocks_writes", Boolean, nullable=False, server_default=sa_false()),
    Column("blocks_ai_explanation", Boolean, nullable=False, server_default=sa_false()),
    Column("status", Text, nullable=False),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
    Column("archived_at", DateTime(timezone=True), nullable=True),
    Column("copied_for_codex_at", DateTime(timezone=True), nullable=True),
    Column("explanation_nl", Text, nullable=False),
    CheckConstraint("severity <> ''", name="ck_system_events_severity_not_empty"),
    CheckConstraint("category <> ''", name="ck_system_events_category_not_empty"),
    CheckConstraint("source_service <> ''", name="ck_system_events_source_service_not_empty"),
    CheckConstraint("source_component <> ''", name="ck_system_events_source_component_not_empty"),
    CheckConstraint("event_code <> ''", name="ck_system_events_event_code_not_empty"),
    CheckConstraint("title_nl <> ''", name="ck_system_events_title_nl_not_empty"),
    CheckConstraint("message_nl <> ''", name="ck_system_events_message_nl_not_empty"),
    CheckConstraint("help_nl <> ''", name="ck_system_events_help_nl_not_empty"),
    CheckConstraint("status <> ''", name="ck_system_events_status_not_empty"),
    CheckConstraint("explanation_nl <> ''", name="ck_system_events_explanation_nl_not_empty"),
)

broker_accounts = Table(
    "broker_accounts",
    metadata,
    Column("broker_account_id", Text, primary_key=True),
    Column("broker_system", Text, nullable=False),
    Column("ibkr_account_ref", Text, nullable=True),
    Column("account_label", Text, nullable=False),
    Column("account_mode", Text, nullable=False),
    Column("connection_status", Text, nullable=False),
    Column("configured", Boolean, nullable=False),
    Column("paper_account", Boolean, nullable=False),
    Column("live_trading_allowed", Boolean, nullable=False),
    Column("source_of_truth_status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=True),
    Column("explanation_nl", Text, nullable=False),
    CheckConstraint("broker_system = 'ibkr'", name="ck_broker_accounts_broker_system_ibkr"),
    CheckConstraint(
        "live_trading_allowed IS FALSE",
        name="ck_broker_accounts_live_trading_allowed_false",
    ),
    CheckConstraint("account_label <> ''", name="ck_broker_accounts_account_label_not_empty"),
    CheckConstraint("account_mode <> ''", name="ck_broker_accounts_account_mode_not_empty"),
    CheckConstraint(
        "connection_status <> ''",
        name="ck_broker_accounts_connection_status_not_empty",
    ),
    CheckConstraint(
        "source_of_truth_status <> ''",
        name="ck_broker_accounts_source_of_truth_status_not_empty",
    ),
    CheckConstraint("explanation_nl <> ''", name="ck_broker_accounts_explanation_nl_not_empty"),
)

broker_sync_runs = Table(
    "broker_sync_runs",
    metadata,
    Column("broker_sync_run_id", Text, primary_key=True),
    Column(
        "broker_account_id",
        Text,
        ForeignKey("broker_accounts.broker_account_id"),
        nullable=True,
    ),
    Column("broker_system", Text, nullable=False),
    Column("sync_mode", Text, nullable=False),
    Column("sync_status", Text, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("planned_data_kinds_json", JSON, nullable=True),
    Column("data_source_types_json", JSON, nullable=True),
    Column("requires_ibkr_configuration", Boolean, nullable=False),
    Column("requires_broker_session", Boolean, nullable=False),
    Column("blocks_suggestions_until_complete", Boolean, nullable=False),
    Column("summary_nl", Text, nullable=False),
    Column("help_nl", Text, nullable=False),
    CheckConstraint("broker_system = 'ibkr'", name="ck_broker_sync_runs_broker_system_ibkr"),
    CheckConstraint("sync_mode <> ''", name="ck_broker_sync_runs_sync_mode_not_empty"),
    CheckConstraint("sync_status <> ''", name="ck_broker_sync_runs_sync_status_not_empty"),
    CheckConstraint("summary_nl <> ''", name="ck_broker_sync_runs_summary_nl_not_empty"),
    CheckConstraint("help_nl <> ''", name="ck_broker_sync_runs_help_nl_not_empty"),
    CheckConstraint(
        "completed_at IS NULL OR completed_at >= started_at",
        name="ck_broker_sync_runs_completed_at_after_started_at",
    ),
)


broker_position_snapshots = Table(
    "broker_position_snapshots",
    metadata,
    Column("broker_position_snapshot_id", Text, primary_key=True),
    Column(
        "broker_sync_run_id",
        Text,
        ForeignKey("broker_sync_runs.broker_sync_run_id"),
        nullable=False,
    ),
    Column(
        "broker_account_id", Text, ForeignKey("broker_accounts.broker_account_id"), nullable=False
    ),
    Column("broker_system", Text, nullable=False),
    Column("imported_at", DateTime(timezone=True), nullable=False),
    Column("asset_identifier", Text, nullable=False),
    Column("asset_symbol", Text, nullable=False),
    Column("asset_type", Text, nullable=False),
    Column("currency", Text, nullable=False),
    Column("quantity", MONEY_NUMERIC, nullable=False),
    Column("average_cost", MONEY_NUMERIC, nullable=True),
    Column("market_value", MONEY_NUMERIC, nullable=True),
    Column("source_data_kind", Text, nullable=False),
    Column("origin", Text, nullable=False),
    Column("source_reference_ids_json", JSON, nullable=True),
    Column("explanation_nl", Text, nullable=False),
    CheckConstraint(
        "broker_system = 'ibkr'",
        name="ck_broker_position_snapshots_broker_system_ibkr",
    ),
    CheckConstraint(
        "asset_identifier <> ''",
        name="ck_broker_position_snapshots_asset_identifier_not_empty",
    ),
    CheckConstraint(
        "asset_symbol <> ''", name="ck_broker_position_snapshots_asset_symbol_not_empty"
    ),
    CheckConstraint("asset_type <> ''", name="ck_broker_position_snapshots_asset_type_not_empty"),
    CheckConstraint("currency <> ''", name="ck_broker_position_snapshots_currency_not_empty"),
    CheckConstraint(
        "source_data_kind <> ''",
        name="ck_broker_position_snapshots_source_data_kind_not_empty",
    ),
    CheckConstraint("origin <> ''", name="ck_broker_position_snapshots_origin_not_empty"),
    CheckConstraint(
        "explanation_nl <> ''",
        name="ck_broker_position_snapshots_explanation_nl_not_empty",
    ),
)

broker_cash_snapshots = Table(
    "broker_cash_snapshots",
    metadata,
    Column("broker_cash_snapshot_id", Text, primary_key=True),
    Column(
        "broker_sync_run_id",
        Text,
        ForeignKey("broker_sync_runs.broker_sync_run_id"),
        nullable=False,
    ),
    Column(
        "broker_account_id", Text, ForeignKey("broker_accounts.broker_account_id"), nullable=False
    ),
    Column("broker_system", Text, nullable=False),
    Column("imported_at", DateTime(timezone=True), nullable=False),
    Column("currency", Text, nullable=False),
    Column("cash_amount", MONEY_NUMERIC, nullable=False),
    Column("source_data_kind", Text, nullable=False),
    Column("origin", Text, nullable=False),
    Column("source_reference_ids_json", JSON, nullable=True),
    Column("explanation_nl", Text, nullable=False),
    CheckConstraint("broker_system = 'ibkr'", name="ck_broker_cash_snapshots_broker_system_ibkr"),
    CheckConstraint("currency <> ''", name="ck_broker_cash_snapshots_currency_not_empty"),
    CheckConstraint(
        "source_data_kind <> ''",
        name="ck_broker_cash_snapshots_source_data_kind_not_empty",
    ),
    CheckConstraint("origin <> ''", name="ck_broker_cash_snapshots_origin_not_empty"),
    CheckConstraint(
        "explanation_nl <> ''", name="ck_broker_cash_snapshots_explanation_nl_not_empty"
    ),
)


broker_execution_snapshots = Table(
    "broker_execution_snapshots",
    metadata,
    Column("broker_execution_snapshot_id", Text, primary_key=True),
    Column(
        "broker_sync_run_id",
        Text,
        ForeignKey("broker_sync_runs.broker_sync_run_id"),
        nullable=False,
    ),
    Column(
        "broker_account_id", Text, ForeignKey("broker_accounts.broker_account_id"), nullable=False
    ),
    Column("broker_system", Text, nullable=False),
    Column("imported_at", DateTime(timezone=True), nullable=False),
    Column("execution_time", DateTime(timezone=True), nullable=False),
    Column("execution_id", Text, nullable=False),
    Column("order_id", Text, nullable=True),
    Column("asset_identifier", Text, nullable=False),
    Column("asset_symbol", Text, nullable=False),
    Column("asset_type", Text, nullable=False),
    Column("side", Text, nullable=False),
    Column("quantity", MONEY_NUMERIC, nullable=False),
    Column("price", MONEY_NUMERIC, nullable=False),
    Column("currency", Text, nullable=False),
    Column("origin", Text, nullable=False),
    Column("source_reference_ids_json", JSON, nullable=True),
    Column("explanation_nl", Text, nullable=False),
    CheckConstraint(
        "broker_system = 'ibkr'", name="ck_broker_execution_snapshots_broker_system_ibkr"
    ),
    CheckConstraint(
        "execution_id <> ''", name="ck_broker_execution_snapshots_execution_id_not_empty"
    ),
    CheckConstraint(
        "asset_identifier <> ''", name="ck_broker_execution_snapshots_asset_identifier_not_empty"
    ),
    CheckConstraint(
        "asset_symbol <> ''", name="ck_broker_execution_snapshots_asset_symbol_not_empty"
    ),
    CheckConstraint("asset_type <> ''", name="ck_broker_execution_snapshots_asset_type_not_empty"),
    CheckConstraint("side <> ''", name="ck_broker_execution_snapshots_side_not_empty"),
    CheckConstraint("quantity > 0", name="ck_broker_execution_snapshots_quantity_gt_0"),
    CheckConstraint("price >= 0", name="ck_broker_execution_snapshots_price_gte_0"),
    CheckConstraint("currency <> ''", name="ck_broker_execution_snapshots_currency_not_empty"),
    CheckConstraint("origin <> ''", name="ck_broker_execution_snapshots_origin_not_empty"),
    CheckConstraint(
        "explanation_nl <> ''", name="ck_broker_execution_snapshots_explanation_nl_not_empty"
    ),
)

broker_commission_snapshots = Table(
    "broker_commission_snapshots",
    metadata,
    Column("broker_commission_snapshot_id", Text, primary_key=True),
    Column(
        "broker_sync_run_id",
        Text,
        ForeignKey("broker_sync_runs.broker_sync_run_id"),
        nullable=False,
    ),
    Column(
        "broker_account_id", Text, ForeignKey("broker_accounts.broker_account_id"), nullable=False
    ),
    Column("broker_system", Text, nullable=False),
    Column("imported_at", DateTime(timezone=True), nullable=False),
    Column("execution_id", Text, nullable=False),
    Column("commission_amount", MONEY_NUMERIC, nullable=False),
    Column("currency", Text, nullable=False),
    Column("realized_pnl", MONEY_NUMERIC, nullable=True),
    Column("source_reference_ids_json", JSON, nullable=True),
    Column("explanation_nl", Text, nullable=False),
    CheckConstraint(
        "broker_system = 'ibkr'", name="ck_broker_commission_snapshots_broker_system_ibkr"
    ),
    CheckConstraint(
        "execution_id <> ''", name="ck_broker_commission_snapshots_execution_id_not_empty"
    ),
    CheckConstraint("currency <> ''", name="ck_broker_commission_snapshots_currency_not_empty"),
    CheckConstraint(
        "explanation_nl <> ''", name="ck_broker_commission_snapshots_explanation_nl_not_empty"
    ),
)


broker_reconciliation_reports = Table(
    "broker_reconciliation_reports",
    metadata,
    Column("broker_reconciliation_report_id", Text, primary_key=True),
    Column(
        "broker_sync_run_id",
        Text,
        ForeignKey("broker_sync_runs.broker_sync_run_id"),
        nullable=False,
    ),
    Column(
        "broker_account_id", Text, ForeignKey("broker_accounts.broker_account_id"), nullable=True
    ),
    Column("broker_system", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("suggestion_policy", Text, nullable=False),
    Column("can_create_suggestions", Boolean, nullable=False),
    Column("can_create_orders", Boolean, nullable=False),
    Column("checked_at", DateTime(timezone=True), nullable=False),
    Column("title_nl", Text, nullable=False),
    Column("summary_nl", Text, nullable=False),
    Column("help_nl", Text, nullable=False),
    CheckConstraint("broker_system = 'ibkr'", name="ck_brr_broker_system_ibkr"),
    CheckConstraint("can_create_orders IS FALSE", name="ck_brr_can_create_orders_false"),
    CheckConstraint("status <> ''", name="ck_brr_status_not_empty"),
    CheckConstraint("suggestion_policy <> ''", name="ck_brr_suggestion_policy_not_empty"),
    CheckConstraint("title_nl <> ''", name="ck_brr_title_nl_not_empty"),
    CheckConstraint("summary_nl <> ''", name="ck_brr_summary_nl_not_empty"),
    CheckConstraint("help_nl <> ''", name="ck_brr_help_nl_not_empty"),
)

broker_reconciliation_differences = Table(
    "broker_reconciliation_differences",
    metadata,
    Column("broker_reconciliation_difference_id", Text, primary_key=True),
    Column(
        "broker_reconciliation_report_id",
        Text,
        ForeignKey("broker_reconciliation_reports.broker_reconciliation_report_id"),
        nullable=False,
    ),
    Column(
        "broker_account_id", Text, ForeignKey("broker_accounts.broker_account_id"), nullable=False
    ),
    Column("broker_system", Text, nullable=False),
    Column("difference_kind", Text, nullable=False),
    Column("severity", Text, nullable=False),
    Column("detected_at", DateTime(timezone=True), nullable=False),
    Column("broker_value", Text, nullable=True),
    Column("local_value", Text, nullable=True),
    Column("asset_identifier", Text, nullable=True),
    Column("currency", Text, nullable=True),
    Column("blocks_suggestions", Boolean, nullable=False),
    Column("requires_manual_review", Boolean, nullable=False),
    Column("summary_nl", Text, nullable=False),
    Column("help_nl", Text, nullable=False),
    Column("source_reference_ids_json", JSON, nullable=True),
    Column("audit_event_ids_json", JSON, nullable=True),
    CheckConstraint("broker_system = 'ibkr'", name="ck_brd_broker_system_ibkr"),
    CheckConstraint("difference_kind <> ''", name="ck_brd_difference_kind_not_empty"),
    CheckConstraint("severity <> ''", name="ck_brd_severity_not_empty"),
    CheckConstraint(
        "severity NOT IN ('blocking', 'critical') OR blocks_suggestions IS TRUE",
        name="ck_brd_blocking_or_critical_requires_block",
    ),
    CheckConstraint("summary_nl <> ''", name="ck_brd_summary_nl_not_empty"),
    CheckConstraint("help_nl <> ''", name="ck_brd_help_nl_not_empty"),
)

external_broker_activities = Table(
    "external_broker_activities",
    metadata,
    Column("external_broker_activity_id", Text, primary_key=True),
    Column(
        "broker_account_id", Text, ForeignKey("broker_accounts.broker_account_id"), nullable=False
    ),
    Column("broker_system", Text, nullable=False),
    Column("detected_at", DateTime(timezone=True), nullable=False),
    Column("origin", Text, nullable=False),
    Column("data_kind", Text, nullable=False),
    Column("related_execution_id", Text, nullable=True),
    Column("related_asset_identifier", Text, nullable=True),
    Column("summary_nl", Text, nullable=False),
    Column("help_nl", Text, nullable=False),
    Column("source_reference_ids_json", JSON, nullable=True),
    Column("audit_event_ids_json", JSON, nullable=True),
    CheckConstraint(
        "broker_system = 'ibkr'",
        name="ck_external_broker_activities_broker_system_ibkr",
    ),
    CheckConstraint("origin <> ''", name="ck_external_broker_activities_origin_not_empty"),
    CheckConstraint("data_kind <> ''", name="ck_external_broker_activities_data_kind_not_empty"),
    CheckConstraint("summary_nl <> ''", name="ck_external_broker_activities_summary_nl_not_empty"),
    CheckConstraint("help_nl <> ''", name="ck_external_broker_activities_help_nl_not_empty"),
)
