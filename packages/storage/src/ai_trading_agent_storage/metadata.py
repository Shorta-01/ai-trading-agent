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
    Integer,
    MetaData,
    Numeric,
    Table,
    Text,
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
