"""SQLAlchemy metadata and table definitions for storage foundation.

Paper setup, audit, and broker sync foundation slice 1 only.
No runtime persistence wiring is enabled yet.
"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    false as sa_false,
)
from sqlalchemy import (
    true as sa_true,
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

trading_settings = Table(
    "trading_settings",
    metadata,
    Column("settings_id", Text, primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("version", Integer, nullable=False),
    Column("allowed_universe_json", JSON, nullable=False),
    Column("user_strategy_json", JSON, nullable=False),
    Column("source", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("explanation_nl", Text, nullable=False),
    CheckConstraint("settings_id <> ''", name="ck_trading_settings_settings_id_not_empty"),
    CheckConstraint("version > 0", name="ck_trading_settings_version_gt_0"),
    CheckConstraint("source <> ''", name="ck_trading_settings_source_not_empty"),
    CheckConstraint("status <> ''", name="ck_trading_settings_status_not_empty"),
    CheckConstraint(
        "explanation_nl <> ''",
        name="ck_trading_settings_explanation_nl_not_empty",
    ),
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

research_sources = Table(
    "research_sources",
    metadata,
    Column("library_source_id", Text, primary_key=True),
    Column("source_kind", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("classification_status", Text, nullable=False),
    Column("extraction_status", Text, nullable=False),
    Column("analysis_status", Text, nullable=False),
    Column("asset_symbol", Text, nullable=True),
    Column("asset_name", Text, nullable=True),
    Column("title", Text, nullable=False),
    Column("document_type", Text, nullable=False),
    Column("source_type", Text, nullable=False),
    Column("source_credibility_level", Text, nullable=True),
    Column("prompt_injection_risk_level", Text, nullable=True),
    Column("content_hash_sha256", Text, nullable=True),
    Column("archive_storage_uri", Text, nullable=True),
    Column("raw_source_available", Boolean, nullable=False, server_default=sa_false()),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("archived_at", DateTime(timezone=True), nullable=True),
    Column("schema_version", Text, nullable=False),
    Column("explanation_nl", Text, nullable=False),
)

research_uploaded_file_metadata = Table(
    "research_uploaded_file_metadata",
    metadata,
    Column(
        "library_source_id",
        Text,
        ForeignKey("research_sources.library_source_id"),
        primary_key=True,
    ),
    Column("original_file_name", Text, nullable=False),
    Column("stored_file_name", Text, nullable=True),
    Column("content_type", Text, nullable=True),
    Column("file_size_bytes", Integer, nullable=True),
    Column("file_hash_sha256", Text, nullable=True),
    Column("detected_language", Text, nullable=True),
    Column("page_count", Integer, nullable=True),
    Column("uploaded_at", DateTime(timezone=True), nullable=False),
    Column("uploaded_by_user", Boolean, nullable=False),
    Column("explanation_nl", Text, nullable=False),
)

research_url_metadata = Table(
    "research_url_metadata",
    metadata,
    Column(
        "library_source_id",
        Text,
        ForeignKey("research_sources.library_source_id"),
        primary_key=True,
    ),
    Column("url", Text, nullable=False),
    Column("normalized_url", Text, nullable=True),
    Column("domain", Text, nullable=True),
    Column("fetched_at", DateTime(timezone=True), nullable=True),
    Column("snapshot_hash_sha256", Text, nullable=True),
    Column("snapshot_storage_uri", Text, nullable=True),
    Column("http_status_code", Integer, nullable=True),
    Column("content_type", Text, nullable=True),
    Column("user_supplied", Boolean, nullable=False),
    Column("explanation_nl", Text, nullable=False),
)

research_user_notes = Table(
    "research_user_notes",
    metadata,
    Column(
        "library_source_id",
        Text,
        ForeignKey("research_sources.library_source_id"),
        primary_key=True,
    ),
    Column("asset_symbol", Text, nullable=True),
    Column("title", Text, nullable=False),
    Column("note_nl", Text, nullable=False),
    Column("thesis_relevance_nl", Text, nullable=True),
    Column("user_confidence_nl", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("explanation_nl", Text, nullable=False),
)

research_document_sets = Table(
    "research_document_sets",
    metadata,
    Column("document_set_id", Text, primary_key=True),
    Column("asset_symbol", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("set_type", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("explanation_nl", Text, nullable=False),
)

research_document_set_members = Table(
    "research_document_set_members",
    metadata,
    Column("member_id", Text, primary_key=True),
    Column(
        "document_set_id",
        Text,
        ForeignKey("research_document_sets.document_set_id"),
        nullable=False,
    ),
    Column(
        "library_source_id", Text, ForeignKey("research_sources.library_source_id"), nullable=False
    ),
    Column("fiscal_year", Integer, nullable=True),
    Column("reporting_period", Text, nullable=True),
    Column("sort_order", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

research_document_classifications = Table(
    "research_document_classifications",
    metadata,
    Column("classification_id", Text, primary_key=True),
    Column(
        "library_source_id", Text, ForeignKey("research_sources.library_source_id"), nullable=False
    ),
    Column("document_type", Text, nullable=False),
    Column("source_type", Text, nullable=False),
    Column("confidence", Text, nullable=False),
    Column("detected_asset_symbol", Text, nullable=True),
    Column("detected_asset_name", Text, nullable=True),
    Column("detected_fiscal_year", Integer, nullable=True),
    Column("detected_reporting_period", Text, nullable=True),
    Column("detected_language", Text, nullable=True),
    Column("needs_user_review", Boolean, nullable=False),
    Column("reason_nl", Text, nullable=False),
    Column("classified_at", DateTime(timezone=True), nullable=False),
    Column("schema_version", Text, nullable=False),
)

research_source_asset_links = Table(
    "research_source_asset_links",
    metadata,
    Column("link_id", Text, primary_key=True),
    Column(
        "library_source_id", Text, ForeignKey("research_sources.library_source_id"), nullable=False
    ),
    Column("asset_symbol", Text, nullable=True),
    Column("asset_name", Text, nullable=True),
    Column("conid", Text, nullable=True),
    Column("isin", Text, nullable=True),
    Column("link_type", Text, nullable=False),
    Column("mapping_confidence", Text, nullable=False),
    Column("auto_linked", Boolean, nullable=False),
    Column("requires_user_confirmation", Boolean, nullable=False),
    Column("confirmed_by_user", Boolean, nullable=False),
    Column("reason_nl", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("confirmed_at", DateTime(timezone=True), nullable=True),
)

research_source_processing_status = Table(
    "research_source_processing_status",
    metadata,
    Column("processing_id", Text, primary_key=True),
    Column(
        "library_source_id", Text, ForeignKey("research_sources.library_source_id"), nullable=False
    ),
    Column("classification_status", Text, nullable=False),
    Column("extraction_status", Text, nullable=False),
    Column("analysis_status", Text, nullable=False),
    Column("readiness_status", Text, nullable=False),
    Column("can_be_used_in_research", Boolean, nullable=False),
    Column("can_be_used_in_suggestions", Boolean, nullable=False),
    Column("needs_user_review", Boolean, nullable=False),
    Column("blocks_suggestions", Boolean, nullable=False),
    Column("last_error_nl", Text, nullable=True),
    Column("checked_at", DateTime(timezone=True), nullable=False),
    Column("reason_nl", Text, nullable=False),
)

research_source_prompt_injection_scans = Table(
    "research_source_prompt_injection_scans",
    metadata,
    Column("scan_id", Text, primary_key=True),
    Column(
        "library_source_id", Text, ForeignKey("research_sources.library_source_id"), nullable=False
    ),
    Column("scan_status", Text, nullable=False),
    Column("risk_level", Text, nullable=False),
    Column("detected_signals_json", Text, nullable=True),
    Column("safe_to_use_as_evidence", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_to_use_as_instruction", Boolean, nullable=False, server_default=sa_false()),
    Column("blocks_suggestions", Boolean, nullable=False, server_default=sa_true()),
    Column("scanned_at", DateTime(timezone=True), nullable=False),
    Column("checked_at", DateTime(timezone=True), nullable=False),
    Column("explanation_nl", Text, nullable=False),
)


research_source_credibility_assessments = Table(
    "research_source_credibility_assessments",
    metadata,
    Column("assessment_id", Text, primary_key=True),
    Column(
        "library_source_id", Text, ForeignKey("research_sources.library_source_id"), nullable=False
    ),
    Column("credibility_status", Text, nullable=False),
    Column("credibility_level", Text, nullable=False),
    Column("source_category", Text, nullable=False),
    Column("assessed_at", DateTime(timezone=True), nullable=False),
    Column("checked_at", DateTime(timezone=True), nullable=False),
    Column("confidence_level", Text, nullable=False),
    Column("credibility_signals_json", Text, nullable=True),
    Column("limitation_notes_nl", Text, nullable=True),
    Column("safe_to_use_as_evidence", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_to_use_for_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("blocks_suggestions", Boolean, nullable=False, server_default=sa_true()),
    Column("explanation_nl", Text, nullable=False),
)


research_source_evidence_items = Table(
    "research_source_evidence_items",
    metadata,
    Column("evidence_item_id", Text, primary_key=True),
    Column(
        "library_source_id",
        Text,
        ForeignKey("research_sources.library_source_id"),
        nullable=False,
    ),
    Column("evidence_type", Text, nullable=False),
    Column("evidence_status", Text, nullable=False),
    Column("extracted_from_kind", Text, nullable=False),
    Column("source_reference_text", Text, nullable=False),
    Column("normalized_evidence_text", Text, nullable=False),
    Column("evidence_summary_nl", Text, nullable=False),
    Column("asset_symbol", Text, nullable=True),
    Column("reporting_period", Text, nullable=True),
    Column("fiscal_year", Integer, nullable=True),
    Column("confidence_level", Text, nullable=False),
    Column("extraction_method", Text, nullable=False),
    Column("source_text_hash_sha256", Text, nullable=True),
    Column("extraction_run_id", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("extracted_at", DateTime(timezone=True), nullable=False),
    Column("safe_to_use_as_evidence", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_to_use_for_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("blocks_suggestions", Boolean, nullable=False, server_default=sa_true()),
    Column("explanation_nl", Text, nullable=False),
)

research_source_evidence_ledger_links = Table(
    "research_source_evidence_ledger_links",
    metadata,
    Column("link_id", Text, primary_key=True),
    Column(
        "library_source_id", Text, ForeignKey("research_sources.library_source_id"), nullable=False
    ),
    Column(
        "evidence_item_id",
        Text,
        ForeignKey("research_source_evidence_items.evidence_item_id"),
        nullable=False,
    ),
    Column(
        "evidence_ledger_item_id", Text, ForeignKey("evidence_items.evidence_id"), nullable=False
    ),
    Column("link_type", Text, nullable=False),
    Column("link_status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("created_by_system", Text, nullable=False),
    Column("lineage_scope", Text, nullable=False),
    Column("source_snapshot_reference", Text, nullable=True),
    Column("evidence_text_hash_sha256", Text, nullable=True),
    Column("gate_context_status", Text, nullable=False),
    Column("safe_to_use_for_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("blocks_suggestions", Boolean, nullable=False, server_default=sa_true()),
    Column("explanation_nl", Text, nullable=False),
)

research_gate_outcomes = Table(
    "research_gate_outcomes",
    metadata,
    Column("gate_outcome_id", Text, primary_key=True),
    Column("gate_name", Text, nullable=False),
    Column("gate_version", Text, nullable=False),
    Column("target_type", Text, nullable=False),
    Column("target_id", Text, nullable=False),
    Column(
        "library_source_id",
        Text,
        ForeignKey("research_sources.library_source_id"),
        nullable=True,
    ),
    Column(
        "evidence_item_id",
        Text,
        ForeignKey("research_source_evidence_items.evidence_item_id"),
        nullable=True,
    ),
    Column(
        "evidence_ledger_item_id",
        Text,
        ForeignKey("evidence_items.evidence_id"),
        nullable=True,
    ),
    Column("outcome_status", Text, nullable=False),
    Column("severity", Text, nullable=False),
    Column("freshness_status", Text, nullable=False),
    Column("checked_at", DateTime(timezone=True), nullable=False),
    Column("valid_until", DateTime(timezone=True), nullable=True),
    Column("expires_at", DateTime(timezone=True), nullable=True),
    Column("source_timestamp", DateTime(timezone=True), nullable=True),
    Column("data_age_seconds", Integer, nullable=True),
    Column("blocking_reason_code", Text, nullable=True),
    Column("blocks_suggestions", Boolean, nullable=False, server_default=sa_true()),
    Column("safe_to_use_as_evidence", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_to_use_for_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("explanation_nl", Text, nullable=False),
    Column("source_reference_ids_json", Text, nullable=True),
    Column("audit_context_json", Text, nullable=True),
)

research_source_conflict_findings = Table(
    "research_source_conflict_findings",
    metadata,
    Column("conflict_finding_id", Text, primary_key=True),
    Column("conflict_status", Text, nullable=False),
    Column("conflict_type", Text, nullable=False),
    Column("severity", Text, nullable=False),
    Column(
        "primary_source_id", Text, ForeignKey("research_sources.library_source_id"), nullable=False
    ),
    Column(
        "conflicting_source_id",
        Text,
        ForeignKey("research_sources.library_source_id"),
        nullable=True,
    ),
    Column(
        "primary_evidence_item_id",
        Text,
        ForeignKey("research_source_evidence_items.evidence_item_id"),
        nullable=True,
    ),
    Column(
        "conflicting_evidence_item_id",
        Text,
        ForeignKey("research_source_evidence_items.evidence_item_id"),
        nullable=True,
    ),
    Column(
        "primary_evidence_ledger_item_id",
        Text,
        ForeignKey("evidence_items.evidence_id"),
        nullable=True,
    ),
    Column(
        "conflicting_evidence_ledger_item_id",
        Text,
        ForeignKey("evidence_items.evidence_id"),
        nullable=True,
    ),
    Column(
        "gate_outcome_id", Text, ForeignKey("research_gate_outcomes.gate_outcome_id"), nullable=True
    ),
    Column("asset_symbol", Text, nullable=True),
    Column("fiscal_year", Integer, nullable=True),
    Column("reporting_period", Text, nullable=True),
    Column("detected_at", DateTime(timezone=True), nullable=False),
    Column("checked_at", DateTime(timezone=True), nullable=False),
    Column("conflict_summary_nl", Text, nullable=False),
    Column("conflict_reason_nl", Text, nullable=False),
    Column("source_reference_ids_json", Text, nullable=True),
    Column("audit_context_json", Text, nullable=True),
    Column("safe_to_use_as_evidence", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_to_use_for_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("blocks_suggestions", Boolean, nullable=False, server_default=sa_true()),
    Column("explanation_nl", Text, nullable=False),
)

source_to_asset_links = Table(
    "source_to_asset_links",
    metadata,
    Column("link_id", Text, primary_key=True),
    Column("asset_id", Text, ForeignKey("asset_master_records.asset_id"), nullable=False),
    Column("target_type", Text, nullable=False),
    Column("target_id", Text, nullable=False),
    Column("link_reason_nl", Text, nullable=False),
    Column("audit_context_json", Text, nullable=True),
    Column("safe_to_use_for_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("blocks_suggestions", Boolean, nullable=False, server_default=sa_true()),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("created_by", Text, nullable=False),
    Column("explanation_nl", Text, nullable=False),
)

watchlist_items = Table(
    "watchlist_items",
    metadata,
    Column("watchlist_item_id", Text, primary_key=True),
    Column("asset_id", Text, ForeignKey("asset_master_records.asset_id"), nullable=True),
    Column("symbol", Text, nullable=False),
    Column("name", Text, nullable=True),
    Column("exchange", Text, nullable=True),
    Column("currency", Text, nullable=True),
    Column("security_type", Text, nullable=True),
    Column("note", Text, nullable=True),
    Column("status", Text, nullable=False),
    Column("source", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    # Task 128: cold-start onboarding columns.
    Column("ibkr_account_id", Text, nullable=True),
    Column(
        "is_starter_seed",
        Boolean,
        nullable=False,
        server_default=sa_false(),
    ),
    Column("seed_version", Text, nullable=True),
    CheckConstraint("symbol <> ''", name="ck_watchlist_items_symbol_not_empty"),
    CheckConstraint(
        "status IN ('active', 'archived')",
        name="ck_watchlist_items_status_valid",
    ),
    CheckConstraint(
        "source IN ('manual', 'cold_start_seed')",
        name="ck_watchlist_items_source_valid",
    ),
)

market_data_snapshots = Table(
    "market_data_snapshots",
    metadata,
    Column("snapshot_id", Text, primary_key=True),
    Column(
        "watchlist_item_id",
        Text,
        ForeignKey("watchlist_items.watchlist_item_id"),
        nullable=False,
    ),
    Column("asset_id", Text, ForeignKey("asset_master_records.asset_id"), nullable=True),
    Column("ibkr_conid", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("security_type", Text, nullable=False),
    Column("exchange", Text, nullable=True),
    Column("primary_exchange", Text, nullable=True),
    Column("currency", Text, nullable=False),
    Column("provider_name", Text, nullable=False),
    Column("data_kind", Text, nullable=False),
    Column("captured_at", DateTime(timezone=True), nullable=False),
    Column("source_timestamp", DateTime(timezone=True), nullable=True),
    Column("stored_at", DateTime(timezone=True), nullable=False),
    Column("freshness_status", Text, nullable=False),
    Column("validation_status", Text, nullable=False),
    Column("blocked_reason", Text, nullable=True),
    Column("raw_reference", Text, nullable=True),
    Column("explanation_nl", Text, nullable=False),
)

asset_master_records = Table(
    "asset_master_records",
    metadata,
    Column("asset_id", Text, primary_key=True),
    Column("canonical_symbol", Text, nullable=False, unique=True),
    Column("asset_name", Text, nullable=False),
    Column("asset_type", Text, nullable=False),
    Column("primary_exchange", Text, nullable=True),
    Column("primary_currency", Text, nullable=True),
    Column("country", Text, nullable=True),
    Column("isin", Text, nullable=True),
    Column("figi", Text, nullable=True),
    Column("cusip", Text, nullable=True),
    Column("ibkr_contract_id", Text, nullable=True),
    Column("sector", Text, nullable=True),
    Column("industry", Text, nullable=True),
    Column("status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("identity_confidence", Text, nullable=False),
    Column("identity_source", Text, nullable=False),
    Column("source_reference_ids_json", JSON, nullable=True),
    Column("audit_context_json", JSON, nullable=True),
    Column("safe_to_use_for_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("blocks_suggestions", Boolean, nullable=False, server_default=sa_true()),
    Column("explanation_nl", Text, nullable=False),
)

asset_identifier_aliases = Table(
    "asset_identifier_aliases",
    metadata,
    Column("alias_id", Text, primary_key=True),
    Column("asset_id", Text, ForeignKey("asset_master_records.asset_id"), nullable=False),
    Column("identifier_type", Text, nullable=False),
    Column("identifier_value", Text, nullable=False),
    Column("source", Text, nullable=False),
    Column("confidence_level", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("explanation_nl", Text, nullable=False),
)

asset_listings = Table(
    "asset_listings",
    metadata,
    Column("listing_id", Text, primary_key=True),
    Column("asset_id", Text, ForeignKey("asset_master_records.asset_id"), nullable=False),
    Column("ibkr_conid", Text, nullable=True),
    Column("symbol", Text, nullable=False),
    Column("local_symbol", Text, nullable=True),
    Column("trading_class", Text, nullable=True),
    Column("security_type", Text, nullable=False),
    Column("asset_class", Text, nullable=True),
    Column("exchange", Text, nullable=True),
    Column("primary_exchange", Text, nullable=True),
    Column("currency", Text, nullable=False),
    Column("listing_country", Text, nullable=True),
    Column("listing_status", Text, nullable=False),
    Column("validation_status", Text, nullable=False),
    Column("validation_source", Text, nullable=True),
    Column("validated_at", DateTime(timezone=True), nullable=True),
    Column("identity_confidence", Text, nullable=False),
    Column("identity_source", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("source_reference_ids_json", JSON, nullable=True),
    Column("audit_context_json", JSON, nullable=True),
    Column("safe_to_use_for_market_data", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_to_use_for_analysis", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_to_use_for_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("blocks_market_data", Boolean, nullable=False, server_default=sa_true()),
    Column("blocks_analysis", Boolean, nullable=False, server_default=sa_true()),
    Column("blocks_suggestions", Boolean, nullable=False, server_default=sa_true()),
    Column("explanation_nl", Text, nullable=False),
)

research_extracted_texts = Table(
    "research_extracted_texts",
    metadata,
    Column("extracted_text_id", Text, primary_key=True),
    Column(
        "library_source_id", Text, ForeignKey("research_sources.library_source_id"), nullable=False
    ),
    Column("source_file_hash_sha256", Text, nullable=True),
    Column("extraction_status", Text, nullable=False),
    Column("extraction_method", Text, nullable=False),
    Column("detected_content_type", Text, nullable=True),
    Column("detected_language", Text, nullable=True),
    Column("character_count", Integer, nullable=True),
    Column("line_count", Integer, nullable=True),
    Column("text_hash_sha256", Text, nullable=True),
    Column("extracted_text_storage_uri", Text, nullable=True),
    Column("preview_text_nl", Text, nullable=True),
    Column("can_be_used_in_research", Boolean, nullable=False, server_default=sa_false()),
    Column("can_be_used_in_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("needs_user_review", Boolean, nullable=False, server_default=sa_true()),
    Column("blocks_suggestions", Boolean, nullable=False, server_default=sa_true()),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("extracted_at", DateTime(timezone=True), nullable=True),
    Column("schema_version", Text, nullable=False),
    Column("reason_nl", Text, nullable=False),
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

evidence_items = Table(
    "evidence_items",
    metadata,
    Column("evidence_id", Text, primary_key=True),
    Column("asset_symbol", Text, nullable=True),
    Column("evidence_type", Text, nullable=False),
    Column("evidence_direction", Text, nullable=False),
    Column("title_nl", Text, nullable=False),
    Column("summary_nl", Text, nullable=False),
    Column("claim_nl", Text, nullable=False),
    Column("source_credibility_level", Text, nullable=False),
    Column("freshness_status", Text, nullable=True),
    Column("prompt_injection_risk_level", Text, nullable=True),
    Column("supports_buy", Boolean, nullable=False, server_default=sa_false()),
    Column("supports_hold", Boolean, nullable=False, server_default=sa_false()),
    Column("supports_sell", Boolean, nullable=False, server_default=sa_false()),
    Column("supports_avoid", Boolean, nullable=False, server_default=sa_false()),
    Column("blocks_action", Boolean, nullable=False, server_default=sa_false()),
    Column("confidence_score", MONEY_NUMERIC, nullable=True),
    Column("observed_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("valid_until", DateTime(timezone=True), nullable=True),
    Column("schema_version", Text, nullable=False),
    Column("metadata_json", JSON, nullable=True),
    Column("explanation_nl", Text, nullable=False),
)


request_logs = Table(
    "request_logs",
    metadata,
    Column("request_log_id", Text, primary_key=True),
    Column("correlation_id", Text, nullable=False),
    Column("parent_correlation_id", Text, nullable=True),
    Column("idempotency_key", Text, nullable=True),
    Column("request_family", Text, nullable=False),
    Column("request_purpose", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("provider_code", Text, nullable=False),
    Column("provider_display_name", Text, nullable=True),
    Column("provider_account_mode", Text, nullable=False),
    Column("provider_environment", Text, nullable=False),
    Column("source_type", Text, nullable=False),
    Column("source_scope", Text, nullable=True),
    Column("source_priority", Integer, nullable=True),
    Column("data_domain", Text, nullable=False),
    Column("asset_id", Text, nullable=True),
    Column("asset_listing_id", Text, nullable=True),
    Column("ibkr_conid", Text, nullable=True),
    Column("symbol", Text, nullable=True),
    Column("currency", Text, nullable=True),
    Column("exchange", Text, nullable=True),
    Column("primary_exchange", Text, nullable=True),
    Column("account_id_hash", Text, nullable=True),
    Column("portfolio_scope", Text, nullable=True),
    Column("request_kind", Text, nullable=False),
    Column("request_target", Text, nullable=False),
    Column("request_parameters_hash", Text, nullable=True),
    Column("request_parameters_redacted_json", JSON, nullable=True),
    Column("requested_time_range_start", DateTime(timezone=True), nullable=True),
    Column("requested_time_range_end", DateTime(timezone=True), nullable=True),
    Column("requested_granularity", Text, nullable=True),
    Column("requested_snapshot_type", Text, nullable=True),
    Column("pacing_bucket", Text, nullable=True),
    Column("pacing_weight", Integer, nullable=True),
    Column("pacing_reset_at", DateTime(timezone=True), nullable=True),
    Column("provider_request_budget_remaining", Integer, nullable=True),
    Column("local_throttle_status", Text, nullable=True),
    Column("retry_count", Integer, nullable=True),
    Column("next_retry_not_before", DateTime(timezone=True), nullable=True),
    Column("request_status", Text, nullable=False),
    Column("provider_status_code", Text, nullable=True),
    Column("provider_error_code", Text, nullable=True),
    Column("provider_error_message_redacted", Text, nullable=True),
    Column("outcome_reason_code", Text, nullable=True),
    Column("received_record_count", Integer, nullable=True),
    Column("stored_record_count", Integer, nullable=True),
    Column("rejected_record_count", Integer, nullable=True),
    Column("null_or_empty_response", Boolean, nullable=True),
    Column("initiated_by", Text, nullable=False),
    Column("initiated_by_job_id", Text, nullable=True),
    Column("triggered_by_event_id", Text, nullable=True),
    Column("linked_readiness_evaluation_id", Text, nullable=True),
    Column("linked_freshness_audit_id", Text, nullable=True),
    Column("audit_notes_nl", Text, nullable=True),
    Column("safe_for_analysis", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_for_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default=sa_false()),
    Column("explanation_nl", Text, nullable=False),
)
provider_sources = Table(
    "provider_sources",
    metadata,
    Column("provider_source_id", Text, primary_key=True),
    Column("provider_code", Text, nullable=False),
    Column("provider_display_name", Text, nullable=True),
    Column("provider_kind", Text, nullable=False),
    Column("data_domain", Text, nullable=False),
    Column("source_type", Text, nullable=False),
    Column("source_authority_level", Text, nullable=True),
    Column("source_credibility_scope", Text, nullable=True),
    Column("source_license_scope", Text, nullable=True),
    Column("source_terms_scope", Text, nullable=True),
    Column("provider_environment", Text, nullable=False),
    Column("provider_account_mode", Text, nullable=False),
    Column("official_source", Boolean, nullable=True),
    Column("broker_source", Boolean, nullable=True),
    Column("user_uploaded_source", Boolean, nullable=True),
    Column("third_party_market_data_source", Boolean, nullable=True),
    Column("derived_source", Boolean, nullable=True),
    Column("source_url_hash", Text, nullable=True),
    Column("source_version", Text, nullable=True),
    Column("source_effective_from", DateTime(timezone=True), nullable=True),
    Column("source_effective_to", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("disabled_at", DateTime(timezone=True), nullable=True),
    Column("disabled_reason", Text, nullable=True),
    Column("audit_notes_nl", Text, nullable=True),
    Column("explanation_nl", Text, nullable=False),
)
freshness_audit_records = Table(
    "freshness_audit_records",
    metadata,
    Column("freshness_audit_id", Text, primary_key=True),
    Column("evaluated_at", DateTime(timezone=True), nullable=False),
    Column("data_domain", Text, nullable=False),
    Column("provider_code", Text, nullable=True),
    Column("source_type", Text, nullable=True),
    Column("asset_id", Text, nullable=True),
    Column("asset_listing_id", Text, nullable=True),
    Column("ibkr_conid", Text, nullable=True),
    Column("snapshot_id", Text, nullable=True),
    Column("snapshot_as_of", DateTime(timezone=True), nullable=True),
    Column("observed_at", DateTime(timezone=True), nullable=True),
    Column("received_at", DateTime(timezone=True), nullable=True),
    Column("stored_at", DateTime(timezone=True), nullable=True),
    Column("age_seconds", Integer, nullable=True),
    Column("freshness_policy_code", Text, nullable=False),
    Column("freshness_status", Text, nullable=False),
    Column("freshness_reason_code", Text, nullable=True),
    Column("freshness_window_seconds", Integer, nullable=True),
    Column("market_session_context", Text, nullable=True),
    Column("market_calendar_status", Text, nullable=True),
    Column("stale_after", DateTime(timezone=True), nullable=True),
    Column("expires_at", DateTime(timezone=True), nullable=True),
    Column("safe_for_analysis", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_for_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default=sa_false()),
    Column("linked_request_log_id", Text, nullable=True),
    Column("linked_readiness_evaluation_id", Text, nullable=True),
    Column("blocker_summary_nl", Text, nullable=True),
    Column("audit_help_nl", Text, nullable=True),
    Column("explanation_nl", Text, nullable=False),
)

market_data_latest_snapshots = Table(
    "market_data_latest_snapshots",
    metadata,
    Column("snapshot_id", Text, primary_key=True),
    Column("ibkr_conid", Text, nullable=False),
    Column("symbol", Text, nullable=True),
    Column("currency", Text, nullable=True),
    Column("asset_class", Text, nullable=True),
    Column("exchange", Text, nullable=True),
    Column("primary_exchange", Text, nullable=True),
    Column("provider_code", Text, nullable=True),
    Column("provider_environment", Text, nullable=True),
    Column("provider_account_mode", Text, nullable=True),
    Column("market_data_type", Text, nullable=True),
    Column("requested_at", DateTime(timezone=True), nullable=True),
    Column("received_at", DateTime(timezone=True), nullable=True),
    Column("provider_as_of", DateTime(timezone=True), nullable=True),
    Column("stored_at", DateTime(timezone=True), nullable=False),
    Column("last_price", Numeric(18, 6), nullable=True),
    Column("bid_price", Numeric(18, 6), nullable=True),
    Column("ask_price", Numeric(18, 6), nullable=True),
    Column("close_price", Numeric(18, 6), nullable=True),
    Column("day_change_percent", Numeric(18, 6), nullable=True),
    Column("status", Text, nullable=False),
    Column("freshness_status", Text, nullable=True),
    Column("explanation_nl", Text, nullable=False),
    Column("request_log_id", Text, nullable=True),
    Column("provider_source_id", Text, nullable=True),
    Column("freshness_audit_id", Text, nullable=True),
    Column("safe_for_analysis", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_for_suggestions", Boolean, nullable=False, server_default=sa_false()),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default=sa_false()),
    CheckConstraint(
        "ibkr_conid <> ''",
        name="ck_market_data_latest_snapshots_ibkr_conid_not_empty",
    ),
)

ibkr_sync_runs = Table(
    "ibkr_sync_runs",
    metadata,
    Column("sync_run_id", Text, primary_key=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("provider_code", Text, nullable=False),
    Column("provider_environment", Text, nullable=False),
    Column("account_mode", Text, nullable=False),
    Column("readonly", Boolean, nullable=False, server_default=sa_true()),
    Column("status", Text, nullable=False),
    Column("account_summary_status", Text, nullable=False),
    Column("positions_status", Text, nullable=False),
    Column("open_orders_status", Text, nullable=False),
    Column("executions_status", Text, nullable=False),
    Column("positions_count", Integer, nullable=False, server_default="0"),
    Column("cash_values_count", Integer, nullable=False, server_default="0"),
    Column("open_orders_count", Integer, nullable=False, server_default="0"),
    Column("executions_count", Integer, nullable=False, server_default="0"),
    Column("status_nl", Text, nullable=True),
    Column("next_step_nl", Text, nullable=True),
    Column("help_nl", Text, nullable=True),
    Column("actions_allowed", Boolean, nullable=False, server_default=sa_false()),
    Column("order_submission_allowed", Boolean, nullable=False, server_default=sa_false()),
    Column("order_modification_allowed", Boolean, nullable=False, server_default=sa_false()),
    Column("order_cancellation_allowed", Boolean, nullable=False, server_default=sa_false()),
    Column("suggestions_allowed", Boolean, nullable=False, server_default=sa_false()),
    Column("stored_at", DateTime(timezone=True), nullable=False),
    # Task 126: ibkr_account_id tagging across IBKR snapshots.
    # Nullable in 126a; 126b's API rewrite populates everywhere and a
    # follow-up migration tightens to NOT NULL.
    Column("ibkr_account_id", Text, nullable=True),
    Column("verified_at", DateTime(timezone=True), nullable=True),
)


ibkr_account_cash_snapshots = Table(
    "ibkr_account_cash_snapshots",
    metadata,
    Column("snapshot_id", Text, primary_key=True),
    Column("sync_run_id", Text, ForeignKey("ibkr_sync_runs.sync_run_id"), nullable=False),
    Column("account_ref", Text, nullable=True),
    Column("base_currency", Text, nullable=False),
    Column("cash", MONEY_NUMERIC, nullable=True),
    Column("available_funds", MONEY_NUMERIC, nullable=True),
    Column("buying_power", MONEY_NUMERIC, nullable=True),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("stored_at", DateTime(timezone=True), nullable=False),
    Column("ibkr_account_id", Text, nullable=True),
)

# Editable IBKR connection + Claude AI settings from the dashboard. A single
# row (config_id="default"). Mirrors alembic/versions/0055_runtime_config.py.
runtime_config = Table(
    "runtime_config",
    metadata,
    Column("config_id", Text, primary_key=True),
    Column("ibkr_enabled", Boolean, nullable=False),
    Column("ibkr_account_id", Text, nullable=True),
    Column("ibkr_host", Text, nullable=True),
    Column("ibkr_port", Integer, nullable=True),
    Column("ibkr_client_id", Integer, nullable=True),
    Column("ai_explanation_enabled", Boolean, nullable=False),
    Column("claude_ai_explanation_model", Text, nullable=True),
    Column("claude_ai_budget_monthly_eur", MONEY_NUMERIC, nullable=True),
    Column("claude_ai_api_key", Text, nullable=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

# Portfolio net-liquidation (NAV) time series for the submission drawdown
# circuit-breaker. Mirrors alembic/versions/0054_ibkr_nav_snapshots.py.
ibkr_nav_snapshots = Table(
    "ibkr_nav_snapshots",
    metadata,
    Column("snapshot_id", Text, primary_key=True),
    Column("ibkr_account_id", Text, nullable=False),
    Column("base_currency", Text, nullable=False),
    Column("nav_value", MONEY_NUMERIC, nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column("stored_at", DateTime(timezone=True), nullable=False),
)

ibkr_position_snapshots = Table(
    "ibkr_position_snapshots",
    metadata,
    Column("snapshot_id", Text, primary_key=True),
    Column("sync_run_id", Text, ForeignKey("ibkr_sync_runs.sync_run_id"), nullable=False),
    Column("account_ref", Text, nullable=True),
    Column("conid", Text, nullable=True),
    Column("symbol", Text, nullable=False),
    Column("security_type", Text, nullable=False),
    Column("currency", Text, nullable=False),
    Column("exchange", Text, nullable=True),
    Column("primary_exchange", Text, nullable=True),
    Column("quantity", MONEY_NUMERIC, nullable=False),
    Column("average_cost", MONEY_NUMERIC, nullable=True),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("stored_at", DateTime(timezone=True), nullable=False),
    Column("ibkr_account_id", Text, nullable=True),
)


ibkr_open_order_snapshots = Table(
    "ibkr_open_order_snapshots",
    metadata,
    Column("snapshot_id", Text, primary_key=True),
    Column("sync_run_id", Text, ForeignKey("ibkr_sync_runs.sync_run_id"), nullable=False),
    Column("account_ref", Text, nullable=True),
    Column("ibkr_order_id", Integer, nullable=False),
    Column("ibkr_perm_id", Integer, nullable=True),
    Column("parent_order_id", Integer, nullable=True),
    Column("client_id", Integer, nullable=True),
    Column("symbol", Text, nullable=False),
    Column("security_type", Text, nullable=False),
    Column("currency", Text, nullable=False),
    Column("exchange", Text, nullable=True),
    Column("primary_exchange", Text, nullable=True),
    Column("action_side", Text, nullable=False),
    Column("order_type", Text, nullable=False),
    Column("quantity", MONEY_NUMERIC, nullable=False),
    Column("limit_price", MONEY_NUMERIC, nullable=True),
    Column("stop_price", MONEY_NUMERIC, nullable=True),
    Column("tif", Text, nullable=True),
    Column("status", Text, nullable=False),
    Column("filled_quantity", MONEY_NUMERIC, nullable=False),
    Column("remaining_quantity", MONEY_NUMERIC, nullable=False),
    Column("average_fill_price", MONEY_NUMERIC, nullable=True),
    Column("last_status_at", DateTime(timezone=True), nullable=True),
    Column("raw_status_reference", Text, nullable=True),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("stored_at", DateTime(timezone=True), nullable=False),
    Column("ibkr_account_id", Text, nullable=True),
)

ibkr_execution_snapshots = Table(
    "ibkr_execution_snapshots",
    metadata,
    Column("snapshot_id", Text, primary_key=True),
    Column("sync_run_id", Text, ForeignKey("ibkr_sync_runs.sync_run_id"), nullable=False),
    Column("account_ref", Text, nullable=True),
    Column("execution_id", Text, nullable=False),
    Column("ibkr_order_id", Integer, nullable=True),
    Column("ibkr_perm_id", Integer, nullable=True),
    Column("symbol", Text, nullable=False),
    Column("security_type", Text, nullable=False),
    Column("currency", Text, nullable=False),
    Column("exchange", Text, nullable=True),
    Column("primary_exchange", Text, nullable=True),
    Column("side", Text, nullable=False),
    Column("quantity", MONEY_NUMERIC, nullable=False),
    Column("price", MONEY_NUMERIC, nullable=False),
    Column("execution_time", DateTime(timezone=True), nullable=False),
    Column("commission", MONEY_NUMERIC, nullable=True),
    Column("commission_currency", Text, nullable=True),
    Column("realized_pnl", MONEY_NUMERIC, nullable=True),
    Column("raw_execution_reference", Text, nullable=True),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("stored_at", DateTime(timezone=True), nullable=False),
    Column("ibkr_account_id", Text, nullable=True),
)


# Task 126: per-snapshot indexes on the new ibkr_account_id column
# so the dashboard's per-account filter doesn't full-scan the
# snapshot tables. Declared at metadata level to keep metadata
# authoritative; the matching ``op.create_index`` calls live in
# alembic/versions/0045_ibkr_account_id_and_mode_tagging.py.
Index(
    "ix_ibkr_sync_runs_ibkr_account_id",
    ibkr_sync_runs.c.ibkr_account_id,
)
Index(
    "ix_ibkr_account_cash_snapshots_ibkr_account_id",
    ibkr_account_cash_snapshots.c.ibkr_account_id,
)
Index(
    "ix_ibkr_nav_snapshots_account_time",
    ibkr_nav_snapshots.c.ibkr_account_id,
    ibkr_nav_snapshots.c.recorded_at,
)
Index(
    "ix_ibkr_position_snapshots_ibkr_account_id",
    ibkr_position_snapshots.c.ibkr_account_id,
)
Index(
    "ix_ibkr_open_order_snapshots_ibkr_account_id",
    ibkr_open_order_snapshots.c.ibkr_account_id,
)
Index(
    "ix_ibkr_execution_snapshots_ibkr_account_id",
    ibkr_execution_snapshots.c.ibkr_account_id,
)


# Task 126: IBKR connection lifecycle audit. Append-only; both
# mode-detection checks (prefix and behavioural) plus connect /
# disconnect / session_error events write rows here. Safety
# booleans hard-False per project doctrine.
ibkr_connection_audit = Table(
    "ibkr_connection_audit",
    metadata,
    Column("audit_id", Text, primary_key=True),
    Column("event_at", DateTime(timezone=True), nullable=False),
    Column("ibkr_account_id", Text, nullable=False),
    Column("event_type", Text, nullable=False),
    Column("account_mode_detected", Text, nullable=True),
    Column("connection_id", Text, nullable=True),
    Column("details_json", JSON, nullable=True),
    Column(
        "safe_for_action_drafts",
        Boolean,
        nullable=False,
        server_default=sa_false(),
    ),
    Column("safe_for_orders", Boolean, nullable=False, server_default=sa_false()),
    CheckConstraint(
        "event_type IN ('connect_attempt','connect_success','connect_refused',"
        "'mode_check_prefix','mode_check_behavioural','disconnect','session_error')",
        name="ck_ibkr_connection_audit_event_type",
    ),
    CheckConstraint(
        "account_mode_detected IS NULL OR "
        "account_mode_detected IN ('paper','live','unknown')",
        name="ck_ibkr_connection_audit_account_mode_detected",
    ),
    Index(
        "ix_ibkr_connection_audit_account_event",
        "ibkr_account_id",
        "event_at",
    ),
)


fx_rate_snapshots = Table(
    "fx_rate_snapshots",
    metadata,
    Column("snapshot_id", Text, primary_key=True),
    Column("provider", Text, nullable=False),
    Column("source", Text, nullable=False),
    Column("base_currency", Text, nullable=False),
    Column("quote_currency", Text, nullable=False),
    Column("pair", Text, nullable=False),
    Column("rate", MONEY_NUMERIC, nullable=False),
    Column("rate_type", Text, nullable=False),
    Column("as_of", DateTime(timezone=True), nullable=False),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("stored_at", DateTime(timezone=True), nullable=False),
    Column("freshness_status", Text, nullable=False),
    Column("validation_status", Text, nullable=False),
    Column("reason_code", Text, nullable=False),
    Column("metadata_json", JSON, nullable=True),
)


market_data_bars = Table(
    "market_data_bars",
    metadata,
    Column("bar_id", Text, primary_key=True),
    Column("ibkr_conid", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("currency", Text, nullable=False),
    Column("exchange", Text, nullable=True),
    Column("primary_exchange", Text, nullable=True),
    Column("provider_code", Text, nullable=False),
    Column("bar_date", Date, nullable=False),
    Column("interval_code", Text, nullable=False),
    Column("open_price", MONEY_NUMERIC, nullable=True),
    Column("high_price", MONEY_NUMERIC, nullable=True),
    Column("low_price", MONEY_NUMERIC, nullable=True),
    Column("close_price", MONEY_NUMERIC, nullable=False),
    Column("adjusted_close_price", MONEY_NUMERIC, nullable=True),
    Column("volume", Numeric(28, 4), nullable=True),
    Column("provider_as_of", DateTime(timezone=True), nullable=True),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("stored_at", DateTime(timezone=True), nullable=False),
    Column("source_type", Text, nullable=False),
    Column("explanation_nl", Text, nullable=False),
    UniqueConstraint(
        "ibkr_conid",
        "interval_code",
        "bar_date",
        "provider_code",
        name="uq_market_data_bars_conid_interval_date_provider",
    ),
)


asset_action_drafts = Table(
    "asset_action_drafts",
    metadata,
    Column("draft_id", Text, primary_key=True),
    Column("decision_package_id", Text, nullable=False),
    Column("decision_package_content_hash", Text, nullable=False),
    Column("ibkr_conid", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("currency", Text, nullable=False),
    Column("exchange", Text, nullable=True),
    Column("primary_exchange", Text, nullable=True),
    Column("account_mode", Text, nullable=False),
    Column("expected_account_mode", Text, nullable=False),
    Column("action_side", Text, nullable=False),
    Column("order_type", Text, nullable=False),
    Column("tif", Text, nullable=False),
    Column("quantity", MONEY_NUMERIC, nullable=False),
    Column("limit_price", MONEY_NUMERIC, nullable=False),
    Column("estimated_order_value", MONEY_NUMERIC, nullable=True),
    Column("estimated_cash_before", MONEY_NUMERIC, nullable=True),
    Column("estimated_cash_after", MONEY_NUMERIC, nullable=True),
    Column("estimated_position_quantity_before", MONEY_NUMERIC, nullable=True),
    Column("estimated_position_quantity_after", MONEY_NUMERIC, nullable=True),
    Column("estimated_position_value_after", MONEY_NUMERIC, nullable=True),
    Column("estimated_portfolio_weight_after_pct", Numeric(10, 6), nullable=True),
    Column("estimated_concentration_impact_pct", Numeric(10, 6), nullable=True),
    Column("orderimpact_base_currency", Text, nullable=True),
    Column("source_action_label", Text, nullable=False),
    Column("source_action_label_nl", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("dry_run_status", Text, nullable=False),
    Column("dry_run_failures_json", JSON, nullable=True),
    Column("blocking_reason", Text, nullable=True),
    Column("rationale_nl", Text, nullable=False),
    Column("explanation_nl", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("safe_for_submission", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
    Column("safe_for_broker_submission", Boolean, nullable=False, server_default="0"),
    Column("estimated_belgian_tob", MONEY_NUMERIC, nullable=True),
    Column("belgian_tob_security_class", Text, nullable=True),
    Column("stop_price", MONEY_NUMERIC, nullable=True),
    Column("trail_amount", MONEY_NUMERIC, nullable=True),
    Column("trail_percent", MONEY_NUMERIC, nullable=True),
    Column("bracket_take_profit_limit_price", MONEY_NUMERIC, nullable=True),
    Column("bracket_stop_loss_price", MONEY_NUMERIC, nullable=True),
    # V1.1 §22.3 conditional-order parent base type. Nullable so
    # existing non-conditional rows stay valid; the dataclass
    # invariant requires non-null when order_type=CONDITIONAL.
    Column("conditional_parent_order_type", Text, nullable=True),
)


asset_action_draft_submissions = Table(
    "asset_action_draft_submissions",
    metadata,
    Column("submission_id", Text, primary_key=True),
    Column("draft_id", Text, nullable=False, unique=True),
    Column("state", Text, nullable=False),
    Column("approval_status", Text, nullable=False),
    Column("approved_at", DateTime(timezone=True), nullable=True),
    Column("approved_by", Text, nullable=True),
    Column("approval_dry_run_status", Text, nullable=True),
    Column("approval_dry_run_failures_json", JSON, nullable=True),
    Column("submitted_at", DateTime(timezone=True), nullable=True),
    Column("ibkr_order_id", Integer, nullable=True),
    Column("ibkr_perm_id", Integer, nullable=True),
    Column("ibkr_client_id", Integer, nullable=True),
    Column("ibkr_status_text", Text, nullable=True),
    Column("filled_quantity", MONEY_NUMERIC, nullable=True),
    Column("remaining_quantity", MONEY_NUMERIC, nullable=True),
    Column("average_fill_price", MONEY_NUMERIC, nullable=True),
    Column("cancelled_at", DateTime(timezone=True), nullable=True),
    Column("cancellation_reason", Text, nullable=True),
    Column("rejected_reason", Text, nullable=True),
    Column("reconciled_at", DateTime(timezone=True), nullable=True),
    Column("account_mode", Text, nullable=False),
    Column("expected_account_mode", Text, nullable=False),
    Column("provider_code", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("last_state_transition_at", DateTime(timezone=True), nullable=False),
    Column("safe_for_broker_submission", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
)


asset_action_draft_events = Table(
    "asset_action_draft_events",
    metadata,
    Column("event_id", Text, primary_key=True),
    Column("draft_id", Text, nullable=False),
    Column("submission_id", Text, nullable=True),
    Column("event_type", Text, nullable=False),
    Column("severity", Text, nullable=False),
    Column("from_state", Text, nullable=True),
    Column("to_state", Text, nullable=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("acknowledged_at", DateTime(timezone=True), nullable=True),
    Column("rationale_nl", Text, nullable=False),
    Column("details_json", JSON, nullable=True),
)


prediction_diary_entries = Table(
    "prediction_diary_entries",
    metadata,
    Column("entry_id", Text, primary_key=True),
    Column("suggestion_id", Text, nullable=False, unique=True),
    Column("forecast_id", Text, nullable=True),
    Column("ibkr_conid", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("currency", Text, nullable=False),
    Column("issued_at", DateTime(timezone=True), nullable=False),
    Column("issued_action_label", Text, nullable=False),
    Column("issued_action_label_nl", Text, nullable=False),
    Column("issued_confidence_label", Text, nullable=False),
    Column("issued_horizon_days", Integer, nullable=False),
    Column("issued_price", MONEY_NUMERIC, nullable=False),
    Column("issued_p10_price", MONEY_NUMERIC, nullable=False),
    Column("issued_p50_price", MONEY_NUMERIC, nullable=False),
    Column("issued_p90_price", MONEY_NUMERIC, nullable=False),
    Column("issued_prob_gain", Numeric(10, 6), nullable=False),
    Column("issued_prob_loss", Numeric(10, 6), nullable=False),
    Column("user_decision", Text, nullable=True),
    Column("realized_price_1d", MONEY_NUMERIC, nullable=True),
    Column("realized_price_1w", MONEY_NUMERIC, nullable=True),
    Column("realized_price_1m", MONEY_NUMERIC, nullable=True),
    Column("realized_return_pct_1d", MONEY_NUMERIC, nullable=True),
    Column("realized_return_pct_1w", MONEY_NUMERIC, nullable=True),
    Column("realized_return_pct_1m", MONEY_NUMERIC, nullable=True),
    Column("outcome_label_1d", Text, nullable=True),
    Column("outcome_label_1w", Text, nullable=True),
    Column("outcome_label_1m", Text, nullable=True),
    Column("outcome_explanation_nl", Text, nullable=False),
    Column("last_evaluated_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("safe_for_self_learning", Boolean, nullable=False, server_default="0"),
    Column("safe_for_model_retraining", Boolean, nullable=False, server_default="0"),
)


decision_package_explanations = Table(
    "decision_package_explanations",
    metadata,
    Column("explanation_id", Text, primary_key=True),
    Column("decision_package_id", Text, nullable=False),
    Column("decision_package_content_hash", Text, nullable=False),
    Column("ibkr_conid", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("model_provider_code", Text, nullable=False),
    Column("model_name", Text, nullable=False),
    Column("model_version", Text, nullable=False),
    Column("input_evidence_hash", Text, nullable=False),
    Column("output_text_hash", Text, nullable=False),
    Column("explanation_nl", Text, nullable=False),
    Column("risk_disclaimer_nl", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("blocking_reason", Text, nullable=True),
    Column("hallucinated_numbers_json", JSON, nullable=True),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("safe_for_self_learning", Boolean, nullable=False, server_default="0"),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
    UniqueConstraint(
        "decision_package_id",
        "decision_package_content_hash",
        name="uq_decision_package_explanations_pkg_hash",
    ),
)


explanation_evidence_ledger = Table(
    "explanation_evidence_ledger",
    metadata,
    Column("ledger_id", Text, primary_key=True),
    Column("explanation_id", Text, nullable=False),
    Column("evidence_kind", Text, nullable=False),
    Column("evidence_reference_id", Text, nullable=False),
    Column("evidence_content_hash", Text, nullable=False),
    Column("linked_at", DateTime(timezone=True), nullable=False),
    Column("safe_for_self_learning", Boolean, nullable=False, server_default="0"),
    Column("safe_for_model_retraining", Boolean, nullable=False, server_default="0"),
)


daily_briefings = Table(
    "daily_briefings",
    metadata,
    Column("briefing_id", Text, primary_key=True),
    Column("briefing_date", Date, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    Column("lookback_started_at", DateTime(timezone=True), nullable=False),
    Column("position_count", Integer, nullable=False),
    Column("base_currency", Text, nullable=True),
    Column("total_position_value", MONEY_NUMERIC, nullable=True),
    Column("cash_total", MONEY_NUMERIC, nullable=True),
    Column("fx_freshness_status", Text, nullable=True),
    Column("new_suggestion_count", Integer, nullable=False),
    Column("new_decision_package_count", Integer, nullable=False),
    Column("new_action_draft_count", Integer, nullable=False),
    Column("diary_outcomes_closed_count", Integer, nullable=False),
    Column("critical_event_count", Integer, nullable=False),
    Column("alert_count", Integer, nullable=False),
    Column("summary_nl", Text, nullable=False),
    Column("help_nl", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("blocking_reason", Text, nullable=True),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
    UniqueConstraint("briefing_date", name="uq_daily_briefings_briefing_date"),
)


briefing_alerts = Table(
    "briefing_alerts",
    metadata,
    Column("alert_id", Text, primary_key=True),
    Column("briefing_id", Text, nullable=False),
    Column("alert_kind", Text, nullable=False),
    Column("severity", Text, nullable=False),
    Column("reference_kind", Text, nullable=True),
    Column("reference_id", Text, nullable=True),
    Column("title_nl", Text, nullable=False),
    Column("body_nl", Text, nullable=False),
    Column("acknowledged_at", DateTime(timezone=True), nullable=True),
    Column("linked_at", DateTime(timezone=True), nullable=False),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
)


scheduler_runs = Table(
    "scheduler_runs",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("job_name", Text, nullable=False),
    Column("scheduled_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("status", Text, nullable=False),
    Column("error_text", Text, nullable=True),
    Column("triggered_by", Text, nullable=False),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
)


universe_scan_runs = Table(
    "universe_scan_runs",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("status", Text, nullable=False),
    Column("triggered_by", Text, nullable=False),
    Column("scanned_count", Integer, nullable=False),
    Column("persisted_count", Integer, nullable=False),
    Column("failed_count", Integer, nullable=False),
    Column("ranked_count", Integer, nullable=False),
    Column("universe_size", Integer, nullable=False),
    Column("error_text", Text, nullable=True),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
)


predictor_backtest_runs = Table(
    "predictor_backtest_runs",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("model_code", Text, nullable=False),
    Column("model_version", Text, nullable=False),
    Column("asset_symbol", Text, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("status", Text, nullable=False),
    Column("window_days", Integer, nullable=False),
    Column("bars_used", Integer, nullable=False),
    Column("brier_score", Numeric(12, 6), nullable=True),
    Column("hit_rate", Numeric(8, 6), nullable=True),
    Column("sharpe_ratio", Numeric(12, 6), nullable=True),
    Column("blocking_reason", Text, nullable=True),
    Column("explanation_nl", Text, nullable=True),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
)


prediction_diary_predictor_contributions = Table(
    "prediction_diary_predictor_contributions",
    metadata,
    Column("contribution_id", Text, primary_key=True),
    Column("diary_entry_id", Text, nullable=False),
    Column("model_code", Text, nullable=False),
    Column("model_version", Text, nullable=False),
    Column("predicted_return_pct", MONEY_NUMERIC, nullable=False),
    Column("predicted_prob_gain", Numeric(10, 6), nullable=False),
    Column("predicted_direction", Text, nullable=False),
    Column("realised_return_pct", MONEY_NUMERIC, nullable=True),
    Column("realised_direction", Text, nullable=True),
    Column("outcome_label", Text, nullable=True),
    Column("brier_score", Numeric(12, 6), nullable=True),
    Column("return_spread_pct", MONEY_NUMERIC, nullable=True),
    Column("explanation_nl", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
)


claude_ai_budget_usage = Table(
    "claude_ai_budget_usage",
    metadata,
    Column("usage_id", Text, primary_key=True),
    Column("budget_month", Text, nullable=False),
    Column("provider_code", Text, nullable=False),
    Column("model_name", Text, nullable=False),
    Column("called_at", DateTime(timezone=True), nullable=False),
    Column("input_units", Integer, nullable=False),
    Column("cached_input_units", Integer, nullable=False),
    Column("output_units", Integer, nullable=False),
    Column("cost_eur", Numeric(12, 6), nullable=False),
    Column("call_kind", Text, nullable=False),
    Column("explanation_nl", Text, nullable=True),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
)


action_draft_order_conditions = Table(
    "action_draft_order_conditions",
    metadata,
    Column("condition_id", Text, primary_key=True),
    Column("draft_id", Text, nullable=False),
    Column("condition_index", Integer, nullable=False),
    Column("condition_kind", Text, nullable=False),
    Column("comparator", Text, nullable=False),
    Column("conjunction", Text, nullable=False),
    Column("trigger_symbol", Text, nullable=True),
    Column("trigger_conid", Text, nullable=True),
    Column("trigger_exchange", Text, nullable=True),
    Column("trigger_price", MONEY_NUMERIC, nullable=True),
    Column("trigger_at_utc", DateTime(timezone=True), nullable=True),
    Column("margin_percent", Numeric(10, 6), nullable=True),
    Column("trigger_volume", BigInteger, nullable=True),
    Column("execution_symbol", Text, nullable=True),
    Column("execution_sec_type", Text, nullable=True),
    Column("execution_exchange", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
)


asset_fundamentals_snapshots = Table(
    "asset_fundamentals_snapshots",
    metadata,
    Column("snapshot_id", Text, primary_key=True),
    Column("ibkr_conid", Text, nullable=True),
    Column("eodhd_symbol", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("sector", Text, nullable=True),
    Column("currency", Text, nullable=True),
    Column("market_cap", Numeric(24, 6), nullable=True),
    Column("pe_ratio", Numeric(20, 6), nullable=True),
    Column("pb_ratio", Numeric(20, 6), nullable=True),
    Column("ev_ebitda", Numeric(20, 6), nullable=True),
    Column("roic_pct", Numeric(20, 6), nullable=True),
    Column("gross_margin_pct", Numeric(20, 6), nullable=True),
    Column("dividend_yield_pct", Numeric(20, 6), nullable=True),
    Column("return_6m_pct", Numeric(20, 6), nullable=True),
    Column("return_12m_pct", Numeric(20, 6), nullable=True),
    Column("raw_payload_hash", Text, nullable=False),
    Column("provider_code", Text, nullable=False),
    Column("fetched_at", DateTime(timezone=True), nullable=False),
    Column("stored_at", DateTime(timezone=True), nullable=False),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    UniqueConstraint(
        "eodhd_symbol",
        "fetched_at",
        name="uq_asset_fundamentals_snapshots_symbol_fetched_at",
    ),
)


asset_decision_packages = Table(
    "asset_decision_packages",
    metadata,
    Column("decision_package_id", Text, primary_key=True),
    Column("content_hash", Text, nullable=False, unique=True),
    Column("ibkr_conid", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("currency", Text, nullable=False),
    Column("risk_profile", Text, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    Column("valid_until", DateTime(timezone=True), nullable=False),
    Column("position_snapshot_id", Text, nullable=True),
    Column("position_quantity", MONEY_NUMERIC, nullable=True),
    Column("position_average_cost", MONEY_NUMERIC, nullable=True),
    Column("cash_snapshot_id", Text, nullable=True),
    Column("cash_base_currency", Text, nullable=True),
    Column("cash_amount", MONEY_NUMERIC, nullable=True),
    Column("market_snapshot_id", Text, nullable=True),
    Column("market_last_price", MONEY_NUMERIC, nullable=True),
    Column("market_freshness_status", Text, nullable=True),
    Column("market_provider_code", Text, nullable=True),
    Column("market_provider_as_of", DateTime(timezone=True), nullable=True),
    Column("fx_pair", Text, nullable=True),
    Column("fx_rate", MONEY_NUMERIC, nullable=True),
    Column("fx_freshness_status", Text, nullable=True),
    Column("forecast_id", Text, nullable=True),
    Column("forecast_model_code", Text, nullable=True),
    Column("forecast_model_version", Text, nullable=True),
    Column("forecast_horizon_days", Integer, nullable=True),
    Column("forecast_p10_price", MONEY_NUMERIC, nullable=True),
    Column("forecast_p50_price", MONEY_NUMERIC, nullable=True),
    Column("forecast_p90_price", MONEY_NUMERIC, nullable=True),
    Column("forecast_prob_gain", Numeric(10, 6), nullable=True),
    Column("forecast_prob_loss", Numeric(10, 6), nullable=True),
    Column("forecast_expected_return_pct", MONEY_NUMERIC, nullable=True),
    Column("forecast_expected_volatility_annual", MONEY_NUMERIC, nullable=True),
    Column("forecast_downside_risk_score", MONEY_NUMERIC, nullable=True),
    Column("forecast_confidence_score", Numeric(10, 6), nullable=True),
    Column("suggestion_id", Text, nullable=True),
    Column("suggestion_model_code", Text, nullable=True),
    Column("suggestion_action_label", Text, nullable=False),
    Column("suggestion_action_label_nl", Text, nullable=False),
    Column("suggestion_confidence_label", Text, nullable=False),
    Column("suggestion_confidence_label_nl", Text, nullable=False),
    Column("suggestion_status", Text, nullable=False),
    Column("has_position", Boolean, nullable=False, server_default="0"),
    Column("gate_outcomes_json", JSON, nullable=True),
    Column("evidence_links_json", JSON, nullable=True),
    Column("audit_links_json", JSON, nullable=True),
    Column("rationale_nl", Text, nullable=False),
    Column("explanation_nl", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("blocking_reason", Text, nullable=True),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
    Column("safe_for_broker_submission", Boolean, nullable=False, server_default="0"),
    Column("research_evidence_count", Integer, nullable=False, server_default="0"),
    Column("research_credibility_summary", Text, nullable=True),
    Column("research_freshness_status", Text, nullable=True),
    Column("research_blocking_reason", Text, nullable=True),
    Column("research_snippet_nl", Text, nullable=True),
)


asset_suggestions = Table(
    "asset_suggestions",
    metadata,
    Column("suggestion_id", Text, primary_key=True),
    Column("ibkr_conid", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("currency", Text, nullable=False),
    Column("forecast_id", Text, nullable=True),
    Column("model_code", Text, nullable=False),
    Column("model_version", Text, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    Column("valid_until", DateTime(timezone=True), nullable=False),
    Column("risk_profile", Text, nullable=False),
    Column("has_position", Boolean, nullable=False, server_default="0"),
    Column("action_label", Text, nullable=False),
    Column("action_label_nl", Text, nullable=False),
    Column("confidence_label", Text, nullable=False),
    Column("confidence_label_nl", Text, nullable=False),
    Column("confidence_score", Numeric(10, 6), nullable=False),
    Column("rationale_nl", Text, nullable=False),
    Column("drivers_json", JSON, nullable=True),
    Column("blockers_json", JSON, nullable=True),
    Column("status", Text, nullable=False),
    Column("blocking_reason", Text, nullable=True),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
    Column("safe_for_orders", Boolean, nullable=False, server_default="0"),
    Column("safe_for_broker_submission", Boolean, nullable=False, server_default="0"),
)


asset_forecasts = Table(
    "asset_forecasts",
    metadata,
    Column("forecast_id", Text, primary_key=True),
    Column("ibkr_conid", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("currency", Text, nullable=False),
    Column("model_code", Text, nullable=False),
    Column("model_version", Text, nullable=False),
    Column("horizon_days", Integer, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    Column("valid_until", DateTime(timezone=True), nullable=False),
    Column("data_points_used", Integer, nullable=False),
    Column("history_first_bar_date", Date, nullable=True),
    Column("history_last_bar_date", Date, nullable=True),
    Column("current_price", MONEY_NUMERIC, nullable=False),
    Column("expected_return_pct", MONEY_NUMERIC, nullable=False),
    Column("p10_price", MONEY_NUMERIC, nullable=False),
    Column("p50_price", MONEY_NUMERIC, nullable=False),
    Column("p90_price", MONEY_NUMERIC, nullable=False),
    Column("prob_gain", Numeric(10, 6), nullable=False),
    Column("prob_loss", Numeric(10, 6), nullable=False),
    Column("prob_loss_gt_5pct", Numeric(10, 6), nullable=False),
    Column("prob_loss_gt_10pct", Numeric(10, 6), nullable=False),
    Column("prob_gain_gt_5pct", Numeric(10, 6), nullable=False),
    Column("prob_gain_gt_10pct", Numeric(10, 6), nullable=False),
    Column("expected_volatility_annual", MONEY_NUMERIC, nullable=False),
    Column("downside_risk_score", MONEY_NUMERIC, nullable=False),
    Column("confidence_score", Numeric(10, 6), nullable=False),
    Column("direction_label", Text, nullable=False),
    Column("direction_label_nl", Text, nullable=False),
    Column("explanation_nl", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("blocking_reason", Text, nullable=True),
    Column("safe_for_analysis", Boolean, nullable=False, server_default="0"),
    Column("safe_for_suggestions", Boolean, nullable=False, server_default="0"),
    Column("safe_for_action_drafts", Boolean, nullable=False, server_default="0"),
)


# Task 127: append-only audit row per APScheduler fire.
scheduled_run_audit = Table(
    "scheduled_run_audit",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("run_at", DateTime(timezone=True), nullable=False),
    Column("run_type", Text, nullable=False),
    Column("ibkr_account_id", Text, nullable=True),
    Column("mode_detected", Text, nullable=False),
    Column("duration_ms", Integer, nullable=True),
    Column("outcome", Text, nullable=False),
    Column("error_details_json", JSON, nullable=True),
    Column("next_scheduled_at", DateTime(timezone=True), nullable=True),
    Column(
        "safe_for_action_drafts",
        Boolean,
        nullable=False,
        server_default=sa_false(),
    ),
    Column("safe_for_orders", Boolean, nullable=False, server_default=sa_false()),
    CheckConstraint(
        "run_type IN ('pre_briefing','morning_briefing','hourly_delta')",
        name="ck_scheduled_run_audit_run_type",
    ),
    CheckConstraint(
        "mode_detected IN ('cold_start','normal','disconnected',"
        "'skipped_locked','skipped_disabled')",
        name="ck_scheduled_run_audit_mode_detected",
    ),
    CheckConstraint(
        "outcome IN ('completed','error')",
        name="ck_scheduled_run_audit_outcome",
    ),
)
Index(
    "ix_scheduled_run_audit_run_at",
    scheduled_run_audit.c.run_at.desc(),
)
Index(
    "ix_scheduled_run_audit_run_type",
    scheduled_run_audit.c.run_type,
)


# Task 127: per-worker scheduler state, heartbeat + next-fire times.
scheduler_state = Table(
    "scheduler_state",
    metadata,
    Column("worker_id", Text, primary_key=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("last_heartbeat_at", DateTime(timezone=True), nullable=False),
    Column("next_pre_briefing_at", DateTime(timezone=True), nullable=True),
    Column("next_hourly_at", DateTime(timezone=True), nullable=True),
)


# Task 128: one row per cold-start seed event. ``UNIQUE`` on
# ``ibkr_account_id`` enforces one-time-only seeding per account.
cold_start_seed_audit = Table(
    "cold_start_seed_audit",
    metadata,
    Column("ibkr_account_id", Text, primary_key=True),
    Column("seeded_at", DateTime(timezone=True), nullable=False),
    Column("seeded_count", Integer, nullable=False),
    Column("failed_conids_json", JSON, nullable=True),
    Column("seed_version", Text, nullable=False),
)


# Task 128: per-account watchlist confirmation state.
watchlist_confirmation_state = Table(
    "watchlist_confirmation_state",
    metadata,
    Column("ibkr_account_id", Text, primary_key=True),
    Column("state", Text, nullable=False),
    Column("last_updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "state IN ('unconfirmed', 'confirmed')",
        name="ck_watchlist_confirmation_state_valid",
    ),
)


# Task 128: append-only audit of every state transition.
watchlist_confirmation_audit = Table(
    "watchlist_confirmation_audit",
    metadata,
    Column("audit_id", Text, primary_key=True),
    Column("event_at", DateTime(timezone=True), nullable=False),
    Column("ibkr_account_id", Text, nullable=False),
    Column("from_state", Text, nullable=False),
    Column("to_state", Text, nullable=False),
    Column("actor", Text, nullable=False),
    Column("row_count_at_event", Integer, nullable=False),
    Column("details_json", JSON, nullable=True),
    CheckConstraint(
        "from_state IN ('absent', 'unconfirmed', 'confirmed')",
        name="ck_watchlist_confirmation_audit_from_state",
    ),
    CheckConstraint(
        "to_state IN ('unconfirmed', 'confirmed')",
        name="ck_watchlist_confirmation_audit_to_state",
    ),
    CheckConstraint(
        "actor IN ('system', 'user')",
        name="ck_watchlist_confirmation_audit_actor",
    ),
)
Index(
    "ix_watchlist_confirmation_audit_account_event",
    watchlist_confirmation_audit.c.ibkr_account_id,
    watchlist_confirmation_audit.c.event_at,
)


# Task 129: EOD market-data runtime tables.
market_data_eod_snapshots = Table(
    "market_data_eod_snapshots",
    metadata,
    Column("snapshot_id", Text, primary_key=True),
    Column("ibkr_conid", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("exchange", Text, nullable=True),
    Column("currency_local", Text, nullable=False),
    Column("as_of_date", Date, nullable=False),
    Column("as_of_close_ts", DateTime(timezone=True), nullable=False),
    Column("ingested_ts", DateTime(timezone=True), nullable=False),
    Column("open_local", MONEY_NUMERIC, nullable=True),
    Column("high_local", MONEY_NUMERIC, nullable=True),
    Column("low_local", MONEY_NUMERIC, nullable=True),
    Column("close_local", MONEY_NUMERIC, nullable=False),
    Column("adj_close_local", MONEY_NUMERIC, nullable=True),
    Column("volume", BigInteger, nullable=True),
    Column("provider", Text, nullable=False),
    Column("provider_response_hash", Text, nullable=False),
    UniqueConstraint(
        "ibkr_conid",
        "as_of_date",
        "provider",
        name="uq_market_data_eod_snapshots_conid_date_provider",
    ),
    CheckConstraint(
        "provider IN ('eodhd', 'manual', 'unknown')",
        name="ck_market_data_eod_snapshots_provider",
    ),
)
Index(
    "ix_market_data_eod_snapshots_conid_date",
    market_data_eod_snapshots.c.ibkr_conid,
    market_data_eod_snapshots.c.as_of_date.desc(),
)


fx_rates = Table(
    "fx_rates",
    metadata,
    Column("base_currency", Text, primary_key=True),
    Column("quote_currency", Text, primary_key=True),
    Column("as_of_date", Date, primary_key=True),
    Column("provider", Text, primary_key=True),
    Column("rate", Numeric(precision=20, scale=8), nullable=False),
    Column("ingested_ts", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "provider IN ('eodhd', 'ecb', 'manual')",
        name="ck_fx_rates_provider",
    ),
)


provider_call_audit = Table(
    "provider_call_audit",
    metadata,
    Column("audit_id", Text, primary_key=True),
    Column("called_at", DateTime(timezone=True), nullable=False),
    Column("provider", Text, nullable=False),
    Column("endpoint", Text, nullable=False),
    Column("request_params_json", JSON, nullable=True),
    Column("response_status", Integer, nullable=True),
    Column("response_size_bytes", Integer, nullable=True),
    Column("duration_ms", Integer, nullable=True),
    Column("error_class", Text, nullable=True),
    Column("error_details_json", JSON, nullable=True),
    Column("account_id", Text, nullable=True),
    Column("triggered_by_run_id", Text, nullable=True),
)
Index(
    "ix_provider_call_audit_called_at",
    provider_call_audit.c.called_at.desc(),
)
Index(
    "ix_provider_call_audit_run_id",
    provider_call_audit.c.triggered_by_run_id,
)


# Task 130: probabilistic-forecast runtime tables.
forecasts = Table(
    "forecasts",
    metadata,
    Column("forecast_run_id", Text, primary_key=True),
    Column("conid", Text, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    Column("generated_by_scheduled_run_id", Text, nullable=False),
    Column("horizon_trading_days", Integer, nullable=False),
    Column("forecast_valid_until", DateTime(timezone=True), nullable=False),
    Column("method", Text, nullable=False),
    Column("history_window_days", Integer, nullable=False),
    Column("history_closes_count", Integer, nullable=False),
    Column("current_price_local", Numeric(precision=20, scale=8), nullable=False),
    Column("currency_local", Text, nullable=False),
    Column("p10_log_return", Numeric(precision=20, scale=10), nullable=False),
    Column("p50_log_return", Numeric(precision=20, scale=10), nullable=False),
    Column("p90_log_return", Numeric(precision=20, scale=10), nullable=False),
    Column("prob_positive", Numeric(precision=8, scale=6), nullable=False),
    Column("prob_loss_gt_5pct", Numeric(precision=8, scale=6), nullable=False),
    Column(
        "expected_volatility_annualized",
        Numeric(precision=10, scale=8),
        nullable=False,
    ),
    Column("confidence_level", Text, nullable=False),
    Column("label", Text, nullable=False),
    Column("block_reason", Text, nullable=True),
    Column("expired_at", DateTime(timezone=True), nullable=True),
    UniqueConstraint(
        "conid",
        "generated_at",
        name="uq_forecasts_conid_generated_at",
    ),
    CheckConstraint(
        "horizon_trading_days > 0",
        name="ck_forecasts_horizon_positive",
    ),
    CheckConstraint(
        "method IN ('historical_bootstrap_v1')",
        name="ck_forecasts_method",
    ),
    CheckConstraint(
        "prob_positive >= 0 AND prob_positive <= 1",
        name="ck_forecasts_prob_positive_range",
    ),
    CheckConstraint(
        "prob_loss_gt_5pct >= 0 AND prob_loss_gt_5pct <= 1",
        name="ck_forecasts_prob_loss_range",
    ),
    CheckConstraint(
        "confidence_level IN ('Laag', 'Gemiddeld', 'Hoog')",
        name="ck_forecasts_confidence",
    ),
    CheckConstraint(
        "label IN ('Kopen', 'Verminderen', 'Verkopen', 'Houden', "
        "'Bekijken', 'Geblokkeerd')",
        name="ck_forecasts_label",
    ),
)
Index(
    "ix_forecasts_conid_generated_at",
    forecasts.c.conid,
    forecasts.c.generated_at.desc(),
)


calibration_diary = Table(
    "calibration_diary",
    metadata,
    Column("forecast_run_id", Text, primary_key=True),
    Column("evaluated_at", DateTime(timezone=True), nullable=False),
    Column(
        "realized_log_return",
        Numeric(precision=20, scale=10),
        nullable=False,
    ),
    Column("hit_status", Text, nullable=False),
    Column(
        "realized_close_price",
        Numeric(precision=20, scale=8),
        nullable=False,
    ),
    CheckConstraint(
        "hit_status IN ('realized_within_p10_p90', 'realized_outside_band',"
        " 'realized_above_p90', 'realized_below_p10')",
        name="ck_calibration_diary_hit_status",
    ),
)


# Task 132: Decision Package — immutable audit-traceable container that
# wraps a single forecast for a single (account, conid) at a single moment
# in time, with every piece of context needed to make the suggested
# action either approvable or refutable. Composed only when the forecast
# label is NOT 'Geblokkeerd'. Append-only; hash-chained per (account,
# conid). Safety booleans are hard-False via CHECK constraint — they only
# flip when the Action Center and approval workflows ship in future
# tasks with their own product locks.
decision_packages = Table(
    "decision_packages",
    metadata,
    Column("decision_package_id", Text, primary_key=True),
    Column("forecast_run_id", Text, nullable=False),
    Column("composed_at", DateTime(timezone=True), nullable=False),
    Column("valid_until", DateTime(timezone=True), nullable=False),
    Column("ibkr_account_id", Text, nullable=False),
    Column("conid", Text, nullable=False),
    # Asset identity snapshot — frozen at composition time so the
    # Decision Package stays valid even if the listing is later
    # updated/archived.
    Column("symbol", Text, nullable=False),
    Column("exchange", Text, nullable=True),
    Column("currency_local", Text, nullable=False),
    Column("asset_class", Text, nullable=True),
    # Holding context snapshot.
    Column("user_holds_position", Boolean, nullable=False),
    Column("held_quantity", Numeric(precision=20, scale=8), nullable=True),
    Column(
        "held_avg_cost_local",
        Numeric(precision=20, scale=8),
        nullable=True,
    ),
    # Current valuation snapshot.
    Column(
        "current_price_local",
        Numeric(precision=20, scale=8),
        nullable=False,
    ),
    Column(
        "current_price_eur", Numeric(precision=20, scale=8), nullable=False
    ),
    Column(
        "as_of_market_data_ts",
        DateTime(timezone=True),
        nullable=False,
    ),
    # Market-data freshness.
    Column("freshness_state", Text, nullable=False),
    Column("data_age_trading_days", Integer, nullable=False),
    # Forecast snapshot — copy of the forecast at composition time.
    Column("forecast_method", Text, nullable=False),
    Column(
        "p10_log_return", Numeric(precision=20, scale=10), nullable=False
    ),
    Column(
        "p50_log_return", Numeric(precision=20, scale=10), nullable=False
    ),
    Column(
        "p90_log_return", Numeric(precision=20, scale=10), nullable=False
    ),
    Column(
        "p10_price_eur", Numeric(precision=20, scale=8), nullable=False
    ),
    Column(
        "p50_price_eur", Numeric(precision=20, scale=8), nullable=False
    ),
    Column(
        "p90_price_eur", Numeric(precision=20, scale=8), nullable=False
    ),
    Column("prob_positive", Numeric(precision=8, scale=6), nullable=False),
    Column(
        "prob_loss_gt_5pct", Numeric(precision=8, scale=6), nullable=False
    ),
    Column(
        "expected_volatility_annualized",
        Numeric(precision=10, scale=8),
        nullable=False,
    ),
    Column("forecast_confidence_level", Text, nullable=False),
    Column("suggested_action_label", Text, nullable=False),
    Column("block_reason", Text, nullable=True),
    # Gate outcomes + evidence references + Dutch explanation.
    Column("gate_outcomes_json", JSON, nullable=False),
    Column("evidence_references_json", JSON, nullable=False),
    Column("deterministic_dutch_explanation", Text, nullable=False),
    # Per-asset hash chain.
    Column("audit_trail_hash", Text, nullable=False),
    Column("previous_package_hash", Text, nullable=True),
    # Hard-False safety booleans (Task 132 product lock §1).
    Column(
        "safe_for_action_drafts",
        Boolean,
        nullable=False,
        server_default="false",
    ),
    Column(
        "safe_for_orders",
        Boolean,
        nullable=False,
        server_default="false",
    ),
    CheckConstraint(
        "freshness_state IN ('fresh', 'stale', 'unavailable')",
        name="ck_decision_packages_freshness_state",
    ),
    CheckConstraint(
        "forecast_method IN ('historical_bootstrap_v1')",
        name="ck_decision_packages_forecast_method",
    ),
    CheckConstraint(
        "forecast_confidence_level IN ('Laag', 'Gemiddeld', 'Hoog')",
        name="ck_decision_packages_forecast_confidence_level",
    ),
    # 'Geblokkeerd' is explicitly excluded — see Task 132 product lock §2.
    CheckConstraint(
        "suggested_action_label IN ('Kopen', 'Verminderen', 'Verkopen', "
        "'Houden', 'Bekijken')",
        name="ck_decision_packages_suggested_action_label",
    ),
    CheckConstraint(
        "prob_positive >= 0 AND prob_positive <= 1",
        name="ck_decision_packages_prob_positive_range",
    ),
    CheckConstraint(
        "prob_loss_gt_5pct >= 0 AND prob_loss_gt_5pct <= 1",
        name="ck_decision_packages_prob_loss_range",
    ),
    CheckConstraint(
        "data_age_trading_days >= 0",
        name="ck_decision_packages_data_age_nonneg",
    ),
    CheckConstraint(
        "safe_for_action_drafts = FALSE",
        name="ck_decision_packages_safe_action_drafts_false",
    ),
    CheckConstraint(
        "safe_for_orders = FALSE",
        name="ck_decision_packages_safe_orders_false",
    ),
)
Index(
    "ix_decision_packages_account_conid_composed",
    decision_packages.c.ibkr_account_id,
    decision_packages.c.conid,
    decision_packages.c.composed_at.desc(),
)
Index(
    "ix_decision_packages_forecast_run_id",
    decision_packages.c.forecast_run_id,
)
Index(
    "ix_decision_packages_audit_hash",
    decision_packages.c.audit_trail_hash,
)


# ---------------------------------------------------------------------------
# Task 133 — Action Drafts + audit (User To-Do layer).
# A draft is a user-promotable IBKR-format order proposal derived from a
# non-Geblokkeerd Decision Package. Editable until approved.
# ``safe_for_submission`` is hard-False via CHECK constraint — Task 134
# (actual submission) flips it conditionally; nothing else may.
# ---------------------------------------------------------------------------
action_drafts = Table(
    "action_drafts",
    metadata,
    Column("action_draft_id", Text, primary_key=True),
    Column(
        "decision_package_id",
        Text,
        ForeignKey("decision_packages.decision_package_id"),
        nullable=True,
    ),
    Column("forecast_run_id", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("created_by", Text, nullable=False),
    Column("ibkr_account_id", Text, nullable=False),
    Column("conid", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("exchange", Text, nullable=False),
    Column("currency_local", Text, nullable=False),
    Column("side", Text, nullable=False),
    Column("quantity", Numeric(precision=20, scale=8), nullable=False),
    Column("order_type", Text, nullable=False),
    Column(
        "limit_price_local",
        Numeric(precision=20, scale=8),
        nullable=False,
    ),
    Column("time_in_force", Text, nullable=False),
    Column(
        "notional_local", Numeric(precision=20, scale=8), nullable=False
    ),
    Column(
        "notional_eur", Numeric(precision=20, scale=8), nullable=False
    ),
    Column(
        "fx_rate_at_creation",
        Numeric(precision=20, scale=8),
        nullable=False,
    ),
    Column(
        "usable_cash_eur_at_creation",
        Numeric(precision=20, scale=8),
        nullable=False,
    ),
    Column(
        "held_quantity_at_creation",
        Numeric(precision=20, scale=8),
        nullable=True,
    ),
    Column("status", Text, nullable=False),
    Column("last_edited_at", DateTime(timezone=True), nullable=True),
    Column("user_approved_at", DateTime(timezone=True), nullable=True),
    Column("dismissed_at", DateTime(timezone=True), nullable=True),
    Column("deleted_at", DateTime(timezone=True), nullable=True),
    Column("dismissed_reason", Text, nullable=True),
    Column("user_note", Text, nullable=True),
    Column(
        "superseded_by_decision_package_id",
        Text,
        ForeignKey("decision_packages.decision_package_id"),
        nullable=True,
    ),
    Column("audit_trail_hash", Text, nullable=False),
    Column("previous_draft_hash", Text, nullable=True),
    Column(
        "safe_for_submission",
        Boolean,
        nullable=False,
        server_default="false",
    ),
    # Task 134 lifecycle columns. ``submission_block_reason`` is the
    # locked enum surfaced to the UI when a safety gate refuses a
    # ``user_approved`` draft at sweep time; ``submission_started_at``
    # marks the moment the worker called ``placeOrder()``;
    # ``terminal_state_at`` marks the moment the lifecycle handler
    # transitioned the draft to a terminal status.
    Column("submission_block_reason", Text, nullable=True),
    Column(
        "submission_started_at", DateTime(timezone=True), nullable=True
    ),
    Column("terminal_state_at", DateTime(timezone=True), nullable=True),
    CheckConstraint(
        "created_by IN ('user', 'system')",
        name="ck_action_drafts_created_by",
    ),
    CheckConstraint(
        "side IN ('BUY', 'SELL')",
        name="ck_action_drafts_side",
    ),
    CheckConstraint(
        "order_type IN ('LMT')",
        name="ck_action_drafts_order_type",
    ),
    CheckConstraint(
        "time_in_force IN ('DAY')",
        name="ck_action_drafts_time_in_force",
    ),
    # Task 134 widens the Task 133 enum with nine in-flight + terminal
    # statuses. Task 135 adds ``requires_manual_review`` (escalation
    # from the reconciler when a timeout sits >24h with no IBKR data).
    # ``submission_block_reason`` lives in its own column; the status
    # enum stays clean.
    CheckConstraint(
        "status IN ('proposed', 'edited', 'user_approved', "
        "'dismissed', 'deleted', 'superseded', 'submitted', "
        "'accepted', 'working', 'filled', 'partially_filled', "
        "'cancelled', 'rejected', 'pending_cancellation', "
        "'awaiting_reply_timeout', 'requires_manual_review')",
        name="ck_action_drafts_status",
    ),
    CheckConstraint(
        "submission_block_reason IS NULL OR submission_block_reason IN ("
        "'cash_insufficient', 'mode_mismatch', 'connection_down', "
        "'account_id_mismatch', 'duplicate_in_flight', "
        "'market_closed', 'cooldown', 'daily_limit', "
        "'soft_drawdown', 'hard_drawdown', 'fomo', "
        "'tick_size_invalid', 'unknown')",
        name="ck_action_drafts_submission_block_reason",
    ),
    CheckConstraint(
        "quantity > 0",
        name="ck_action_drafts_quantity_positive",
    ),
    CheckConstraint(
        "limit_price_local > 0",
        name="ck_action_drafts_limit_price_positive",
    ),
    CheckConstraint(
        "safe_for_submission = FALSE",
        name="ck_action_drafts_safe_for_submission_false",
    ),
)
Index(
    "ix_action_drafts_account_status_created",
    action_drafts.c.ibkr_account_id,
    action_drafts.c.status,
    action_drafts.c.created_at.desc(),
)
Index(
    "ix_action_drafts_decision_package_id",
    action_drafts.c.decision_package_id,
)
Index(
    "ix_action_drafts_conid_account_status",
    action_drafts.c.conid,
    action_drafts.c.ibkr_account_id,
    action_drafts.c.status,
)


action_draft_audit = Table(
    "action_draft_audit",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "action_draft_id",
        Text,
        ForeignKey("action_drafts.action_draft_id"),
        nullable=False,
    ),
    Column("event_at", DateTime(timezone=True), nullable=False),
    Column("event_type", Text, nullable=False),
    Column("before_state_json", JSON, nullable=True),
    Column("after_state_json", JSON, nullable=True),
    Column("actor", Text, nullable=False),
    CheckConstraint(
        "event_type IN ('created', 'edited', 'approved', "
        "'dismissed', 'deleted', 'superseded')",
        name="ck_action_draft_audit_event_type",
    ),
    CheckConstraint(
        "actor IN ('user', 'system')",
        name="ck_action_draft_audit_actor",
    ),
)
Index(
    "ix_action_draft_audit_draft_id_event_at",
    action_draft_audit.c.action_draft_id,
    action_draft_audit.c.event_at,
)


# ---------------------------------------------------------------------------
# Task 134 — IBKR submission lifecycle, audit, executions, and the
# per-account behavioural guardrail thresholds. Every new table is
# append-only at the storage layer; the only mutation path for a draft's
# in-flight state is the natural status transition on ``action_drafts``.
# ---------------------------------------------------------------------------

ibkr_submission_audit = Table(
    "ibkr_submission_audit",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "action_draft_id",
        Text,
        ForeignKey("action_drafts.action_draft_id"),
        nullable=False,
    ),
    Column("submitted_at", DateTime(timezone=True), nullable=False),
    Column("sent_to_account_id", Text, nullable=False),
    Column("sent_account_mode", Text, nullable=False),
    Column("ibkr_perm_id", BigInteger, nullable=True),
    Column("ibkr_order_id", Integer, nullable=True),
    Column("contract_json", JSON, nullable=False),
    Column("order_json", JSON, nullable=False),
    Column("gateway_session_id", Text, nullable=False),
    Column("result", Text, nullable=False),
    Column("error_class", Text, nullable=True),
    Column("error_message_dutch", Text, nullable=True),
    CheckConstraint(
        "sent_account_mode IN ('paper', 'live')",
        name="ck_ibkr_submission_audit_sent_account_mode",
    ),
    CheckConstraint(
        "result IN ('placed', 'rejected_at_send', 'connection_lost')",
        name="ck_ibkr_submission_audit_result",
    ),
)
Index(
    "ix_ibkr_submission_audit_draft_submitted",
    ibkr_submission_audit.c.action_draft_id,
    ibkr_submission_audit.c.submitted_at,
)
Index(
    "ix_ibkr_submission_audit_account_submitted",
    ibkr_submission_audit.c.sent_to_account_id,
    ibkr_submission_audit.c.submitted_at,
)


ibkr_submission_lifecycle = Table(
    "ibkr_submission_lifecycle",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "action_draft_id",
        Text,
        ForeignKey("action_drafts.action_draft_id"),
        nullable=False,
    ),
    Column("event_at", DateTime(timezone=True), nullable=False),
    Column("ibkr_perm_id", BigInteger, nullable=False),
    Column("event_type", Text, nullable=False),
    Column("from_status", Text, nullable=True),
    Column("to_status", Text, nullable=True),
    Column("ibkr_raw_status", Text, nullable=True),
    Column(
        "fill_price_local", Numeric(precision=20, scale=8), nullable=True
    ),
    Column("fill_quantity", Numeric(precision=20, scale=8), nullable=True),
    Column("commission", Numeric(precision=20, scale=8), nullable=True),
    Column("commission_currency", Text, nullable=True),
    Column("raw_callback_json", JSON, nullable=False),
    CheckConstraint(
        "event_type IN ('status_change', 'fill', "
        "'commission_report', 'cancellation_request')",
        name="ck_ibkr_submission_lifecycle_event_type",
    ),
)
Index(
    "ix_ibkr_submission_lifecycle_draft_event_at",
    ibkr_submission_lifecycle.c.action_draft_id,
    ibkr_submission_lifecycle.c.event_at,
)
Index(
    "ix_ibkr_submission_lifecycle_perm_id",
    ibkr_submission_lifecycle.c.ibkr_perm_id,
)


ibkr_executions = Table(
    "ibkr_executions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ibkr_exec_id", Text, nullable=False, unique=True),
    Column("ibkr_perm_id", BigInteger, nullable=False),
    Column(
        "action_draft_id",
        Text,
        ForeignKey("action_drafts.action_draft_id"),
        nullable=False,
    ),
    Column("account_id", Text, nullable=False),
    Column("conid", Text, nullable=False),
    Column("side", Text, nullable=False),
    Column(
        "fill_price_local",
        Numeric(precision=20, scale=8),
        nullable=False,
    ),
    Column("fill_quantity", Numeric(precision=20, scale=8), nullable=False),
    Column("fill_time", DateTime(timezone=True), nullable=False),
    Column("commission", Numeric(precision=20, scale=8), nullable=False),
    Column("commission_currency", Text, nullable=False),
    Column("exchange", Text, nullable=False),
    CheckConstraint(
        "side IN ('BUY', 'SELL')",
        name="ck_ibkr_executions_side",
    ),
    CheckConstraint(
        "fill_price_local > 0",
        name="ck_ibkr_executions_fill_price_positive",
    ),
    CheckConstraint(
        "fill_quantity > 0",
        name="ck_ibkr_executions_fill_quantity_positive",
    ),
    CheckConstraint(
        "commission >= 0",
        name="ck_ibkr_executions_commission_non_negative",
    ),
)
Index(
    "ix_ibkr_executions_account_conid_time",
    ibkr_executions.c.account_id,
    ibkr_executions.c.conid,
    ibkr_executions.c.fill_time,
)
Index(
    "ix_ibkr_executions_action_draft_id",
    ibkr_executions.c.action_draft_id,
)
Index(
    "ix_ibkr_executions_perm_id",
    ibkr_executions.c.ibkr_perm_id,
)


behavioural_guardrail_settings = Table(
    "behavioural_guardrail_settings",
    metadata,
    Column("ibkr_account_id", Text, primary_key=True),
    Column(
        "daily_max_approvals",
        Integer,
        nullable=False,
        server_default="5",
    ),
    Column(
        "cooldown_seconds",
        Integer,
        nullable=False,
        server_default="60",
    ),
    Column(
        "anti_revenge_window_hours",
        Integer,
        nullable=False,
        server_default="72",
    ),
    Column(
        "anti_revenge_loss_threshold_pct",
        Numeric(precision=8, scale=4),
        nullable=False,
        server_default="1.0",
    ),
    Column(
        "soft_drawdown_pct",
        Numeric(precision=8, scale=4),
        nullable=False,
        server_default="5.0",
    ),
    Column(
        "soft_drawdown_window_days",
        Integer,
        nullable=False,
        server_default="5",
    ),
    Column(
        "hard_drawdown_pct",
        Numeric(precision=8, scale=4),
        nullable=False,
        server_default="10.0",
    ),
    Column(
        "hard_drawdown_window_days",
        Integer,
        nullable=False,
        server_default="20",
    ),
    Column(
        "fomo_drift_pct",
        Numeric(precision=8, scale=4),
        nullable=False,
        server_default="1.5",
    ),
    Column("last_updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "daily_max_approvals > 0",
        name="ck_behavioural_guardrail_daily_max_positive",
    ),
    CheckConstraint(
        "cooldown_seconds >= 0",
        name="ck_behavioural_guardrail_cooldown_non_negative",
    ),
    CheckConstraint(
        "anti_revenge_loss_threshold_pct >= 0",
        name="ck_behavioural_guardrail_anti_revenge_non_negative",
    ),
    CheckConstraint(
        "soft_drawdown_pct >= 0",
        name="ck_behavioural_guardrail_soft_drawdown_non_negative",
    ),
    CheckConstraint(
        "hard_drawdown_pct >= 0",
        name="ck_behavioural_guardrail_hard_drawdown_non_negative",
    ),
    CheckConstraint(
        "fomo_drift_pct >= 0",
        name="ck_behavioural_guardrail_fomo_non_negative",
    ),
)


# ---------------------------------------------------------------------------
# Task 135 — Reconciliation audit + manual review queue + unmatched
# executions. Every table is append-only at the storage layer except for
# ``manual_review_queue.resolution_status`` and
# ``unmatched_execution_audit.resolution_status`` which can transition
# pending → resolved/acknowledged once the user has handled the row.
# ---------------------------------------------------------------------------

reconciliation_audit = Table(
    "reconciliation_audit",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reconciliation_run_id", Text, nullable=False),
    Column(
        "action_draft_id",
        Text,
        ForeignKey("action_drafts.action_draft_id"),
        nullable=True,
    ),
    Column("event_at", DateTime(timezone=True), nullable=False),
    Column("pass_name", Text, nullable=False),
    Column("divergence_type", Text, nullable=False),
    Column("before_status", Text, nullable=True),
    Column("after_status", Text, nullable=True),
    Column("ibkr_evidence_json", JSON, nullable=False),
    Column("notes_dutch", Text, nullable=True),
    CheckConstraint(
        "pass_name IN ('orphaned_execution', 'stale_in_flight', "
        "'timeout_recovery')",
        name="ck_reconciliation_audit_pass_name",
    ),
    CheckConstraint(
        "divergence_type IN ("
        "'missing_execution_applied', "
        "'status_corrected_to_filled', "
        "'status_corrected_to_cancelled', "
        "'status_corrected_to_rejected', "
        "'status_corrected_to_partially_filled', "
        "'timeout_recovered_to_terminal', "
        "'timeout_flagged_manual_review', "
        "'unmatched_execution', "
        "'terminal_state_divergence_logged')",
        name="ck_reconciliation_audit_divergence_type",
    ),
)
Index(
    "ix_reconciliation_audit_run",
    reconciliation_audit.c.reconciliation_run_id,
)
Index(
    "ix_reconciliation_audit_draft_event",
    reconciliation_audit.c.action_draft_id,
    reconciliation_audit.c.event_at,
)


unmatched_execution_audit = Table(
    "unmatched_execution_audit",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("event_at", DateTime(timezone=True), nullable=False),
    Column("ibkr_perm_id", BigInteger, nullable=False),
    Column("ibkr_exec_id", Text, nullable=False, unique=True),
    Column("account_id", Text, nullable=False),
    Column("conid", Text, nullable=False),
    Column("side", Text, nullable=False),
    Column(
        "fill_price_local",
        Numeric(precision=20, scale=8),
        nullable=False,
    ),
    Column(
        "fill_quantity", Numeric(precision=20, scale=8), nullable=False
    ),
    Column("fill_time", DateTime(timezone=True), nullable=False),
    Column("raw_execution_json", JSON, nullable=False),
    Column(
        "resolution_status",
        Text,
        nullable=False,
        server_default="unresolved",
    ),
    CheckConstraint(
        "side IN ('BUY', 'SELL')",
        name="ck_unmatched_execution_audit_side",
    ),
    CheckConstraint(
        "resolution_status IN ('unresolved', 'manually_matched', "
        "'ignored')",
        name="ck_unmatched_execution_audit_resolution_status",
    ),
    CheckConstraint(
        "fill_price_local > 0",
        name="ck_unmatched_execution_audit_fill_price_positive",
    ),
    CheckConstraint(
        "fill_quantity > 0",
        name="ck_unmatched_execution_audit_fill_quantity_positive",
    ),
)
Index(
    "ix_unmatched_execution_audit_account",
    unmatched_execution_audit.c.account_id,
    unmatched_execution_audit.c.fill_time,
)


manual_review_queue = Table(
    "manual_review_queue",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("flagged_at", DateTime(timezone=True), nullable=False),
    Column(
        "action_draft_id",
        Text,
        ForeignKey("action_drafts.action_draft_id"),
        nullable=False,
    ),
    Column("reason", Text, nullable=False),
    Column("details_dutch", Text, nullable=False),
    Column(
        "resolution_status",
        Text,
        nullable=False,
        server_default="pending",
    ),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
    Column("resolution_note", Text, nullable=True),
    CheckConstraint(
        "reason IN ('timeout_24h_no_data', "
        "'terminal_state_divergence', "
        "'unmatched_execution_no_draft')",
        name="ck_manual_review_queue_reason",
    ),
    CheckConstraint(
        "resolution_status IN ('pending', 'resolved', "
        "'acknowledged')",
        name="ck_manual_review_queue_resolution_status",
    ),
)
Index(
    "ix_manual_review_queue_status",
    manual_review_queue.c.resolution_status,
    manual_review_queue.c.flagged_at,
)
Index(
    "ix_manual_review_queue_draft",
    manual_review_queue.c.action_draft_id,
)


reconciliation_run_audit = Table(
    "reconciliation_run_audit",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "reconciliation_run_id",
        Text,
        nullable=False,
        unique=True,
    ),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("account_id", Text, nullable=False),
    Column(
        "pass_a_orphaned_count",
        Integer,
        nullable=False,
        server_default="0",
    ),
    Column(
        "pass_b_stale_count",
        Integer,
        nullable=False,
        server_default="0",
    ),
    Column(
        "pass_c_timeout_count",
        Integer,
        nullable=False,
        server_default="0",
    ),
    Column(
        "divergences_found",
        Integer,
        nullable=False,
        server_default="0",
    ),
    Column("mode_detected", Text, nullable=False),
    Column("error_details_json", JSON, nullable=True),
    CheckConstraint(
        "mode_detected IN ('completed', 'skipped_locked', "
        "'skipped_disconnected', 'error')",
        name="ck_reconciliation_run_audit_mode_detected",
    ),
)
Index(
    "ix_reconciliation_run_audit_account_started",
    reconciliation_run_audit.c.account_id,
    reconciliation_run_audit.c.started_at,
)
