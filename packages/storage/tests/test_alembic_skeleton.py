from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from ai_trading_agent_storage.alembic_helpers import (
    get_target_metadata,
    is_migration_skeleton_ready,
)
from ai_trading_agent_storage.metadata import metadata

ROOT = Path(__file__).resolve().parents[1]


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def test_alembic_files_and_versions_folder_exist() -> None:
    assert (ROOT / "alembic.ini").exists()
    assert (ROOT / "alembic" / "env.py").exists()
    assert (ROOT / "alembic" / "versions").exists()


def test_target_metadata_is_package_metadata() -> None:
    assert get_target_metadata() is metadata


def test_skeleton_ready_without_database_connection() -> None:
    assert is_migration_skeleton_ready() is True


def test_exactly_seventy_revision_files_exist_with_expected_names() -> None:
    versions_dir = ROOT / "alembic" / "versions"
    revision_files = sorted(
        path.name for path in versions_dir.glob("*.py") if path.name != ".gitkeep"
    )
    assert revision_files == [
        "0001_paper_setup_audit_foundation.py",
        "0002_broker_accounts_and_sync_runs.py",
        "0003_broker_position_and_cash_snapshots.py",
        "0004_broker_execution_and_commission_snapshots.py",
        "0005_broker_reconciliation_schema.py",
        "0006_external_broker_activities.py",
        "0007_system_events.py",
        "0008_trading_settings.py",
        "0009_evidence_ledger.py",
        "0010_research_source_archive.py",
        "0011_research_extracted_text.py",
        "0012_research_source_prompt_injection_scan.py",
        "0013_research_source_credibility_assessments.py",
        "0014_research_source_evidence_items.py",
        "0015_research_source_evidence_ledger_links.py",
        "0016_research_gate_outcomes.py",
        "0017_research_source_conflict_findings.py",
        "0018_asset_master_identity_foundation.py",
        "0019_source_to_asset_linking_foundation.py",
        "0020_watchlist_foundation.py",
        "0021_market_data_storage_foundation.py",
        "0022_asset_listing_identity_foundation.py",
        "0023_request_log_provider_freshness_contracts.py",
        "0024_market_data_latest_snapshots.py",
        "0025_ibkr_sync_snapshot_storage.py",
        "0026_fx_rate_snapshot_storage.py",
        "0027_market_data_bars_and_asset_forecasts.py",
        "0028_asset_suggestions.py",
        "0029_asset_decision_packages.py",
        "0030_asset_action_drafts.py",
        "0031_action_draft_submissions_and_events.py",
        "0032_prediction_diary_entries.py",
        "0033_decision_package_research_evidence.py",
        "0034_decision_package_explanations.py",
        "0035_action_draft_belgian_tob.py",
        "0036_daily_briefings.py",
        "0037_scheduler_runs.py",
        "0038_asset_fundamentals_snapshots.py",
        "0039_universe_scan_runs.py",
        "0040_action_draft_order_vocabulary.py",
        "0041_predictor_backtest_runs.py",
        "0042_prediction_diary_per_predictor.py",
        "0043_claude_ai_budget_usage.py",
        "0044_action_draft_conditional_orders.py",
        "0045_ibkr_account_id_and_mode_tagging.py",
        "0046_scheduled_run_audit_and_scheduler_state.py",
        "0047_cold_start_and_watchlist_confirmation.py",
        "0048_market_data_eod_and_fx_runtime.py",
        "0049_forecasts_and_calibration_diary.py",
        "0050_decision_packages.py",
        "0051_action_drafts_and_audit.py",
        "0052_ibkr_submission_lifecycle_audit_and_executions.py",
        "0053_reconciliation_audit_and_manual_review.py",
        "0054_ibkr_nav_snapshots.py",
        "0055_runtime_config.py",
        "0056_runtime_config_universe_scan.py",
        "0057_runtime_config_order_policy.py",
        "0058_runtime_config_scheduler.py",
        "0059_runtime_config_data_windows.py",
        "0060_runtime_config_worker_sweeps.py",
        "0061_runtime_config_advanced.py",
        "0062_runtime_config_sharpe_thresholds.py",
        "0063_runtime_config_forecast_market.py",
        "0064_runtime_config_execution_gates.py",
        "0065_runtime_config_predictor_tuning.py",
        "0066_asset_suggestions_grid_columns.py",
        "0067_runtime_config_market_aware_scheduler.py",
        "0068_daily_digests.py",
        "0069_runtime_config_notifications.py",
        "0070_runtime_config_ai_features.py",
        "0071_orchestrator_scoring_verdicts.py",
        "0072_earnings_events.py",
        "0073_watchlist_preferences.py",
        "0074_runtime_config_software_pause.py",
        "0075_runtime_config_profit_target.py",
        "0076_dividend_events.py",
        "0077_monthly_report_archive.py",
        "0078_sell_signal_cards.py",
        "0079_macro_index_snapshots.py",
        "0080_dashboard_query_indexes.py",
    ]


def test_0002_revision_content_and_safety_guards() -> None:
    revision_path = ROOT / "alembic" / "versions" / "0002_broker_accounts_and_sync_runs.py"
    content = revision_path.read_text(encoding="utf-8")
    normalized = _normalize(content)

    assert "def upgrade()" in content
    assert "def downgrade()" in content
    assert "broker account and sync run foundation" in content.lower()
    assert "ibkr mirror/reconciliation foundation slice 1" in content.lower()

    assert "broker_accounts" in content
    assert "broker_sync_runs" in content

    drop_sync_position = content.find('op.drop_table("broker_sync_runs")')
    drop_accounts_position = content.find('op.drop_table("broker_accounts")')
    assert drop_sync_position >= 0
    assert drop_accounts_position >= 0
    assert drop_sync_position < drop_accounts_position

    forbidden_tokens = [
        "password",
        "access_token",
        "refresh_token",
        "api_key",
        "secret_value",
        "ibapi",
        "ib_insync",
    ]
    for token in forbidden_tokens:
        assert token not in normalized

    forbidden_import_tokens = [
        "portfolio_outlook_domain",
        "portfolio_outlook_portfolio",
        "portfolio_outlook_api",
        "worker",
        "ibkr",
    ]
    for token in forbidden_import_tokens:
        assert f"import {token}" not in normalized
        assert f"from {token} import" not in normalized


def test_postgresql_create_table_compilation_includes_broker_tables() -> None:
    table_names = [
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
    ]
    for table_name in table_names:
        sql = str(CreateTable(metadata.tables[table_name]).compile(dialect=postgresql.dialect()))
        assert f"create table {table_name}" in sql.lower()


def test_0003_revision_content_and_safety_guards() -> None:
    revision_path = ROOT / "alembic" / "versions" / "0003_broker_position_and_cash_snapshots.py"
    content = revision_path.read_text(encoding="utf-8")
    normalized = _normalize(content)

    assert "def upgrade()" in content
    assert "def downgrade()" in content
    assert "broker position and cash snapshot foundation" in content.lower()
    assert "ibkr mirror/reconciliation foundation slice 2" in content.lower()
    assert "broker_position_snapshots" in content
    assert "broker_cash_snapshots" in content

    drop_cash_position = content.find('op.drop_table("broker_cash_snapshots")')
    drop_position_position = content.find('op.drop_table("broker_position_snapshots")')
    assert drop_cash_position >= 0
    assert drop_position_position >= 0
    assert drop_cash_position < drop_position_position

    forbidden_tokens = [
        "password",
        "access_token",
        "refresh_token",
        "api_key",
        "secret_value",
        "ibapi",
        "ib_insync",
    ]
    for token in forbidden_tokens:
        assert token not in normalized

    forbidden_import_tokens = ["domain", "portfolio", "api", "worker", "ibkr"]
    for token in forbidden_import_tokens:
        assert f"import {token}" not in normalized
        assert f"from {token} import" not in normalized


def test_0004_revision_content_and_safety_guards() -> None:
    revision_path = (
        ROOT / "alembic" / "versions" / "0004_broker_execution_and_commission_snapshots.py"
    )
    content = revision_path.read_text(encoding="utf-8")
    normalized = _normalize(content)

    assert "def upgrade()" in content
    assert "def downgrade()" in content
    assert "broker execution and commission snapshot foundation" in content.lower()
    assert "ibkr mirror/reconciliation foundation slice 3" in content.lower()
    assert "broker_execution_snapshots" in content
    assert "broker_commission_snapshots" in content

    drop_commission = content.find('op.drop_table("broker_commission_snapshots")')
    drop_execution = content.find('op.drop_table("broker_execution_snapshots")')
    assert drop_commission >= 0 and drop_execution >= 0 and drop_commission < drop_execution

    for token in [
        "password",
        "access_token",
        "refresh_token",
        "api_key",
        "secret_value",
        "ibapi",
        "ib_insync",
    ]:
        assert token not in normalized
    for token in ["domain", "portfolio", "api", "worker", "ibkr"]:
        assert f"import {token}" not in normalized
        assert f"from {token} import" not in normalized


def test_0005_revision_content_and_safety_guards() -> None:
    revision_path = ROOT / "alembic" / "versions" / "0005_broker_reconciliation_schema.py"
    content = revision_path.read_text(encoding="utf-8")
    normalized = _normalize(content)
    assert "def upgrade()" in content
    assert "def downgrade()" in content
    assert "broker reconciliation schema foundation" in content.lower()
    assert "ibkr mirror/reconciliation foundation slice 4" in content.lower()
    assert "broker_reconciliation_reports" in content
    assert "broker_reconciliation_differences" in content
    drop_differences = content.find('op.drop_table("broker_reconciliation_differences")')
    drop_reports = content.find('op.drop_table("broker_reconciliation_reports")')
    assert drop_differences >= 0 and drop_reports >= 0 and drop_differences < drop_reports
    for token in [
        "password",
        "access_token",
        "refresh_token",
        "api_key",
        "secret_value",
        "ibapi",
        "ib_insync",
    ]:
        assert token not in normalized
    for token in ["domain", "portfolio", "api", "worker", "ibkr"]:
        assert f"import {token}" not in normalized
        assert f"from {token} import" not in normalized


def test_0006_revision_content_and_safety_guards() -> None:
    revision_path = ROOT / "alembic" / "versions" / "0006_external_broker_activities.py"
    content = revision_path.read_text(encoding="utf-8")
    normalized = _normalize(content)
    assert "def upgrade()" in content
    assert "def downgrade()" in content
    assert "external broker activity schema foundation" in content.lower()
    assert "ibkr mirror/reconciliation foundation slice 5" in content.lower()
    assert "external broker activity storage only" in content.lower()
    assert "external_broker_activities" in content
    assert "create_table" in content
    assert "drop_table" in content
    assert content.find('op.drop_table("external_broker_activities")') >= 0
    for token in [
        "password",
        "access_token",
        "refresh_token",
        "api_key",
        "secret_value",
        "ibapi",
        "ib_insync",
    ]:
        assert token not in normalized
    for token in ["domain", "portfolio", "api", "worker", "ibkr"]:
        assert f"import {token}" not in normalized
        assert f"from {token} import" not in normalized


def test_0010_research_archive_migration_has_tables_and_downgrade_order() -> None:
    revision_path = ROOT / "alembic" / "versions" / "0010_research_source_archive.py"
    content = revision_path.read_text(encoding="utf-8")

    assert 'revision = "0010_research_source_archive"' in content
    assert 'down_revision = "0009_evidence_ledger"' in content

    table_names = [
        "research_sources",
        "research_uploaded_file_metadata",
        "research_url_metadata",
        "research_user_notes",
        "research_document_sets",
        "research_document_set_members",
        "research_document_classifications",
        "research_source_asset_links",
        "research_source_processing_status",
    ]
    for table_name in table_names:
        assert f'"{table_name}"' in content

    drop_order = [
        "research_source_processing_status",
        "research_source_asset_links",
        "research_document_classifications",
        "research_document_set_members",
        "research_document_sets",
        "research_user_notes",
        "research_url_metadata",
        "research_uploaded_file_metadata",
        "research_sources",
    ]
    drop_positions = [content.find(f'op.drop_table("{name}")') for name in drop_order]
    assert all(position >= 0 for position in drop_positions)
    assert drop_positions == sorted(drop_positions)


def test_0011_research_extracted_text_migration_has_table_and_downgrade() -> None:
    revision_path = ROOT / "alembic" / "versions" / "0011_research_extracted_text.py"
    content = revision_path.read_text(encoding="utf-8")
    assert 'revision = "0011_research_extracted_text"' in content
    assert 'down_revision = "0010_research_source_archive"' in content
    assert '"research_extracted_texts"' in content
    assert 'op.drop_table("research_extracted_texts")' in content
