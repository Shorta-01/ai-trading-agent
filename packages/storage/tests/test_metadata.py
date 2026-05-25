from sqlalchemy import DateTime, Numeric

from ai_trading_agent_storage.metadata import metadata


def test_metadata_imports_and_expected_tables_only() -> None:
    expected = {
        "paper_portfolio_setups",
        "paper_cash_accounts",
        "audit_events",
        "broker_accounts",
        "broker_sync_runs",
        "broker_position_snapshots",
        "broker_cash_snapshots",
        "broker_execution_snapshots",
        "broker_commission_snapshots",
        "broker_reconciliation_reports",
        "broker_reconciliation_differences",
        "external_broker_activities",
        "system_events",
        "trading_settings",
        "evidence_items",
        "research_sources",
        "research_uploaded_file_metadata",
        "research_url_metadata",
        "research_user_notes",
        "research_document_sets",
        "research_document_set_members",
        "research_document_classifications",
        "research_source_asset_links",
        "research_source_processing_status",
        "research_source_prompt_injection_scans",
        "research_extracted_texts",
        "research_source_credibility_assessments",
        "research_source_evidence_items",
        "research_source_evidence_ledger_links",
        "research_gate_outcomes",
        "research_source_conflict_findings",
        "asset_master_records",
        "asset_identifier_aliases",
        "asset_listings",
        "source_to_asset_links",
        "watchlist_items",
        "market_data_snapshots",
        "request_logs",
        "provider_sources",
        "freshness_audit_records",
        "market_data_latest_snapshots",
        "ibkr_sync_runs",
        "ibkr_account_cash_snapshots",
        "ibkr_position_snapshots",
        "ibkr_open_order_snapshots",
        "ibkr_execution_snapshots",
        "fx_rate_snapshots",
        "market_data_bars",
        "asset_forecasts",
        "asset_suggestions",
        "asset_decision_packages",
        "asset_action_drafts",
        "asset_action_draft_submissions",
        "asset_action_draft_events",
        "prediction_diary_entries",
        "decision_package_explanations",
        "explanation_evidence_ledger",
        "daily_briefings",
        "briefing_alerts",
        "scheduler_runs",
        "asset_fundamentals_snapshots",
        "universe_scan_runs",
        "predictor_backtest_runs",
        "prediction_diary_predictor_contributions",
        "claude_ai_budget_usage",
        "action_draft_order_conditions",
        "ibkr_connection_audit",
        "scheduled_run_audit",
        "scheduler_state",
        "cold_start_seed_audit",
        "watchlist_confirmation_state",
        "watchlist_confirmation_audit",
        "market_data_eod_snapshots",
        "fx_rates",
        "provider_call_audit",
        "forecasts",
        "calibration_diary",
    }
    assert metadata is not None
    assert set(metadata.tables) == expected


def test_money_columns_are_numeric() -> None:
    assert isinstance(
        metadata.tables["paper_portfolio_setups"].c.starting_cash_amount.type,
        Numeric,
    )
    assert isinstance(
        metadata.tables["paper_cash_accounts"].c.initial_paper_cash_amount.type,
        Numeric,
    )


def test_timestamp_columns_are_timezone_aware() -> None:
    columns = [
        metadata.tables["paper_portfolio_setups"].c.created_at,
        metadata.tables["paper_portfolio_setups"].c.updated_at,
        metadata.tables["paper_cash_accounts"].c.created_at,
        metadata.tables["audit_events"].c.occurred_at,
        metadata.tables["audit_events"].c.created_at,
        metadata.tables["broker_accounts"].c.created_at,
        metadata.tables["broker_accounts"].c.updated_at,
        metadata.tables["broker_sync_runs"].c.started_at,
        metadata.tables["broker_sync_runs"].c.completed_at,
        metadata.tables["broker_position_snapshots"].c.imported_at,
        metadata.tables["broker_cash_snapshots"].c.imported_at,
        metadata.tables["broker_execution_snapshots"].c.imported_at,
        metadata.tables["broker_execution_snapshots"].c.execution_time,
        metadata.tables["broker_commission_snapshots"].c.imported_at,
        metadata.tables["broker_reconciliation_reports"].c.checked_at,
        metadata.tables["broker_reconciliation_differences"].c.detected_at,
        metadata.tables["external_broker_activities"].c.detected_at,
        metadata.tables["system_events"].c.created_at,
        metadata.tables["system_events"].c.resolved_at,
        metadata.tables["system_events"].c.archived_at,
        metadata.tables["system_events"].c.copied_for_codex_at,
        metadata.tables["trading_settings"].c.created_at,
        metadata.tables["trading_settings"].c.updated_at,
    ]
    for column in columns:
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True


def test_paper_cash_accounts_has_expected_setup_fk() -> None:
    setup_id_fk_targets = {
        fk.target_fullname for fk in metadata.tables["paper_cash_accounts"].c.setup_id.foreign_keys
    }
    assert setup_id_fk_targets == {"paper_portfolio_setups.setup_id"}


def test_broker_sync_runs_has_expected_broker_account_fk() -> None:
    broker_account_fk_targets = {
        fk.target_fullname
        for fk in metadata.tables["broker_sync_runs"].c.broker_account_id.foreign_keys
    }
    assert broker_account_fk_targets == {"broker_accounts.broker_account_id"}


def test_required_paper_only_columns_exist() -> None:
    table = metadata.tables["paper_portfolio_setups"]
    for name in [
        "paper_only",
        "real_money_used",
        "broker_order_created",
        "live_trading_enabled",
        "user_confirmed_paper_only",
        "user_confirmed_no_real_money",
        "user_confirmed_no_broker_order",
    ]:
        assert name in table.c


def test_broker_tables_have_expected_columns() -> None:
    broker_accounts_expected = {
        "broker_account_id",
        "broker_system",
        "ibkr_account_ref",
        "account_label",
        "account_mode",
        "connection_status",
        "configured",
        "paper_account",
        "live_trading_allowed",
        "source_of_truth_status",
        "created_at",
        "updated_at",
        "explanation_nl",
    }
    broker_sync_runs_expected = {
        "broker_sync_run_id",
        "broker_account_id",
        "broker_system",
        "sync_mode",
        "sync_status",
        "started_at",
        "completed_at",
        "planned_data_kinds_json",
        "data_source_types_json",
        "requires_ibkr_configuration",
        "requires_broker_session",
        "blocks_suggestions_until_complete",
        "summary_nl",
        "help_nl",
    }
    assert set(metadata.tables["broker_accounts"].c.keys()) == broker_accounts_expected
    assert set(metadata.tables["broker_sync_runs"].c.keys()) == broker_sync_runs_expected


def test_no_secret_like_column_names_and_no_legacy_table_names() -> None:
    forbidden_columns = {
        "password",
        "api_key",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "credential",
    }
    forbidden_table_fragments = {"portfolio_outlook", "pom"}

    for table_name, table in metadata.tables.items():
        table_name_lower = table_name.lower()
        assert not any(fragment in table_name_lower for fragment in forbidden_table_fragments)

        for column_name in table.c.keys():
            column_name_lower = column_name.lower()
            assert not any(token in column_name_lower for token in forbidden_columns)


def test_trading_settings_table_has_expected_columns() -> None:
    expected = {
        "settings_id",
        "created_at",
        "updated_at",
        "version",
        "allowed_universe_json",
        "user_strategy_json",
        "source",
        "status",
        "explanation_nl",
    }
    assert set(metadata.tables["trading_settings"].c.keys()) == expected


def test_broker_snapshot_tables_have_expected_columns() -> None:
    broker_position_expected = {
        "broker_position_snapshot_id",
        "broker_sync_run_id",
        "broker_account_id",
        "broker_system",
        "imported_at",
        "asset_identifier",
        "asset_symbol",
        "asset_type",
        "currency",
        "quantity",
        "average_cost",
        "market_value",
        "source_data_kind",
        "origin",
        "source_reference_ids_json",
        "explanation_nl",
    }
    broker_cash_expected = {
        "broker_cash_snapshot_id",
        "broker_sync_run_id",
        "broker_account_id",
        "broker_system",
        "imported_at",
        "currency",
        "cash_amount",
        "source_data_kind",
        "origin",
        "source_reference_ids_json",
        "explanation_nl",
    }
    assert set(metadata.tables["broker_position_snapshots"].c.keys()) == broker_position_expected
    assert set(metadata.tables["broker_cash_snapshots"].c.keys()) == broker_cash_expected


def test_fx_rate_snapshot_table_has_expected_columns() -> None:
    expected = {
        "snapshot_id", "provider", "source", "base_currency", "quote_currency",
        "pair", "rate", "rate_type", "as_of", "received_at", "stored_at",
        "freshness_status", "validation_status", "reason_code", "metadata_json",
    }
    assert set(metadata.tables["fx_rate_snapshots"].c.keys()) == expected


def test_broker_snapshot_numeric_columns_are_numeric_and_not_float() -> None:
    numeric_columns = [
        metadata.tables["broker_position_snapshots"].c.quantity,
        metadata.tables["broker_position_snapshots"].c.average_cost,
        metadata.tables["broker_position_snapshots"].c.market_value,
        metadata.tables["broker_cash_snapshots"].c.cash_amount,
    ]
    for column in numeric_columns:
        assert isinstance(column.type, Numeric)
        assert column.type.precision == 20
        assert column.type.scale == 6


def test_broker_snapshot_foreign_keys() -> None:
    assert {
        fk.target_fullname
        for fk in metadata.tables["broker_position_snapshots"].c.broker_sync_run_id.foreign_keys
    } == {"broker_sync_runs.broker_sync_run_id"}
    assert {
        fk.target_fullname
        for fk in metadata.tables["broker_position_snapshots"].c.broker_account_id.foreign_keys
    } == {"broker_accounts.broker_account_id"}
    assert {
        fk.target_fullname
        for fk in metadata.tables["broker_cash_snapshots"].c.broker_sync_run_id.foreign_keys
    } == {"broker_sync_runs.broker_sync_run_id"}
    assert {
        fk.target_fullname
        for fk in metadata.tables["broker_cash_snapshots"].c.broker_account_id.foreign_keys
    } == {"broker_accounts.broker_account_id"}


def test_broker_execution_and_commission_tables_have_expected_columns() -> None:
    assert set(metadata.tables["broker_execution_snapshots"].c.keys()) == {
        "broker_execution_snapshot_id",
        "broker_sync_run_id",
        "broker_account_id",
        "broker_system",
        "imported_at",
        "execution_time",
        "execution_id",
        "order_id",
        "asset_identifier",
        "asset_symbol",
        "asset_type",
        "side",
        "quantity",
        "price",
        "currency",
        "origin",
        "source_reference_ids_json",
        "explanation_nl",
    }
    assert set(metadata.tables["broker_commission_snapshots"].c.keys()) == {
        "broker_commission_snapshot_id",
        "broker_sync_run_id",
        "broker_account_id",
        "broker_system",
        "imported_at",
        "execution_id",
        "commission_amount",
        "currency",
        "realized_pnl",
        "source_reference_ids_json",
        "explanation_nl",
    }


def test_broker_execution_and_commission_numeric_columns() -> None:
    for col in [
        metadata.tables["broker_execution_snapshots"].c.quantity,
        metadata.tables["broker_execution_snapshots"].c.price,
        metadata.tables["broker_commission_snapshots"].c.commission_amount,
        metadata.tables["broker_commission_snapshots"].c.realized_pnl,
    ]:
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 20
        assert col.type.scale == 6


def test_broker_execution_and_commission_foreign_keys() -> None:
    assert {
        fk.target_fullname
        for fk in metadata.tables["broker_execution_snapshots"].c.broker_sync_run_id.foreign_keys
    } == {"broker_sync_runs.broker_sync_run_id"}
    assert {
        fk.target_fullname
        for fk in metadata.tables["broker_execution_snapshots"].c.broker_account_id.foreign_keys
    } == {"broker_accounts.broker_account_id"}
    assert {
        fk.target_fullname
        for fk in metadata.tables["broker_commission_snapshots"].c.broker_sync_run_id.foreign_keys
    } == {"broker_sync_runs.broker_sync_run_id"}
    assert {
        fk.target_fullname
        for fk in metadata.tables["broker_commission_snapshots"].c.broker_account_id.foreign_keys
    } == {"broker_accounts.broker_account_id"}
    assert metadata.tables["broker_commission_snapshots"].c.execution_id.foreign_keys == set()


def test_broker_reconciliation_tables_have_expected_columns() -> None:
    assert set(metadata.tables["broker_reconciliation_reports"].c.keys()) == {
        "broker_reconciliation_report_id", "broker_sync_run_id", "broker_account_id",
        "broker_system", "status", "suggestion_policy", "can_create_suggestions",
        "can_create_orders", "checked_at", "title_nl", "summary_nl", "help_nl",
    }
    assert set(metadata.tables["broker_reconciliation_differences"].c.keys()) == {
        "broker_reconciliation_difference_id", "broker_reconciliation_report_id",
        "broker_account_id", "broker_system", "difference_kind", "severity",
        "detected_at", "broker_value", "local_value", "asset_identifier", "currency",
        "blocks_suggestions", "requires_manual_review", "summary_nl", "help_nl",
        "source_reference_ids_json", "audit_event_ids_json",
    }

def test_broker_reconciliation_foreign_keys() -> None:
    assert {
        fk.target_fullname
        for fk in metadata.tables["broker_reconciliation_reports"].c.broker_sync_run_id.foreign_keys
    } == {"broker_sync_runs.broker_sync_run_id"}
    assert {
        fk.target_fullname
        for fk in metadata.tables["broker_reconciliation_reports"].c.broker_account_id.foreign_keys
    } == {"broker_accounts.broker_account_id"}
    assert {
        fk.target_fullname
        for fk in metadata.tables[
            "broker_reconciliation_differences"
        ].c.broker_reconciliation_report_id.foreign_keys
    } == {"broker_reconciliation_reports.broker_reconciliation_report_id"}
    assert {
        fk.target_fullname
        for fk in metadata.tables[
            "broker_reconciliation_differences"
        ].c.broker_account_id.foreign_keys
    } == {"broker_accounts.broker_account_id"}


def test_external_broker_activities_have_expected_columns_and_fk() -> None:
    assert set(metadata.tables["external_broker_activities"].c.keys()) == {
        "external_broker_activity_id",
        "broker_account_id",
        "broker_system",
        "detected_at",
        "origin",
        "data_kind",
        "related_execution_id",
        "related_asset_identifier",
        "summary_nl",
        "help_nl",
        "source_reference_ids_json",
        "audit_event_ids_json",
    }
    assert {
        fk.target_fullname
        for fk in metadata.tables["external_broker_activities"].c.broker_account_id.foreign_keys
    } == {"broker_accounts.broker_account_id"}
