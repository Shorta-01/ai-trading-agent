from dataclasses import fields
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from ai_trading_agent_storage.repository_contracts import (
    BrokerAccountRepository,
    BrokerCashSnapshotRecord,
    BrokerCommissionSnapshotRecord,
    BrokerExecutionSnapshotRecord,
    BrokerPositionSnapshotRecord,
    BrokerReconciliationRepository,
    BrokerSnapshotRepository,
    BrokerStorageUnitOfWork,
    BrokerSyncRunRepository,
    CreatePaperPortfolioSetupRequest,
    ExternalBrokerActivityRepository,
    PaperPortfolioSetupRecord,
    PaperPortfolioSetupRepositoryProtocol,
    RepositoryHealthStatus,
    StorageListResult,
    StorageReadResult,
    StorageWriteResult,
    build_repository_health_not_connected,
    repository_interfaces_are_defined,
)


def test_repository_contracts_import_and_helpers() -> None:
    assert repository_interfaces_are_defined() is True
    health = build_repository_health_not_connected()
    assert isinstance(health, RepositoryHealthStatus)
    assert health.connected is False


def test_repository_health_defaults_are_safe_and_dutch() -> None:
    health = build_repository_health_not_connected()
    assert health.available is False
    assert health.connected is False
    assert health.migrations_current is False
    assert health.read_only is True
    assert "repository" in health.explanation_nl.lower()


def test_broker_dto_decimal_fields_use_decimal_not_float() -> None:
    position = BrokerPositionSnapshotRecord(
        broker_position_snapshot_id="ps-1",
        broker_sync_run_id="sr-1",
        broker_account_id="ba-1",
        broker_system="ibkr",
        imported_at=datetime.now(UTC),
        asset_identifier="US0378331005",
        asset_symbol="AAPL",
        asset_type="stock",
        currency="USD",
        quantity=Decimal("10"),
        average_cost=Decimal("100.12"),
        market_value=Decimal("1020.55"),
        source_data_kind="snapshot",
        origin="broker",
        source_reference_ids_json=None,
        explanation_nl="Positie import.",
    )
    cash = BrokerCashSnapshotRecord(
        broker_cash_snapshot_id="cs-1",
        broker_sync_run_id="sr-1",
        broker_account_id="ba-1",
        broker_system="ibkr",
        imported_at=datetime.now(UTC),
        currency="USD",
        cash_amount=Decimal("1000.00"),
        source_data_kind="snapshot",
        origin="broker",
        source_reference_ids_json=None,
        explanation_nl="Cash import.",
    )
    execution = BrokerExecutionSnapshotRecord(
        broker_execution_snapshot_id="es-1",
        broker_sync_run_id="sr-1",
        broker_account_id="ba-1",
        broker_system="ibkr",
        imported_at=datetime.now(UTC),
        execution_time=datetime.now(UTC),
        execution_id="ex-1",
        order_id=None,
        asset_identifier="US0378331005",
        asset_symbol="AAPL",
        asset_type="stock",
        side="buy",
        quantity=Decimal("1"),
        price=Decimal("150.50"),
        currency="USD",
        origin="broker",
        source_reference_ids_json=None,
        explanation_nl="Execution import.",
    )
    commission = BrokerCommissionSnapshotRecord(
        broker_commission_snapshot_id="co-1",
        broker_sync_run_id="sr-1",
        broker_account_id="ba-1",
        broker_system="ibkr",
        imported_at=datetime.now(UTC),
        execution_time=datetime.now(UTC),
        execution_id="ex-1",
        commission_amount=Decimal("1.25"),
        currency="USD",
        realized_pnl=Decimal("5.00"),
        source_reference_ids_json=None,
        explanation_nl="Commissie import.",
    )

    assert isinstance(position.quantity, Decimal)
    assert isinstance(position.average_cost, Decimal)
    assert position.average_cost is None or isinstance(position.average_cost, Decimal)
    assert isinstance(cash.cash_amount, Decimal)
    assert isinstance(execution.quantity, Decimal)
    assert isinstance(execution.price, Decimal)
    assert isinstance(commission.commission_amount, Decimal)
    assert commission.realized_pnl is None or isinstance(commission.realized_pnl, Decimal)
    assert not isinstance(position.quantity, float)


def test_contracts_do_not_include_secret_like_fields() -> None:
    forbidden = (
        "password",
        "api_key",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "credential",
    )
    types_to_check = [
        StorageWriteResult,
        StorageReadResult,
        StorageListResult,
        RepositoryHealthStatus,
        BrokerPositionSnapshotRecord,
        BrokerCashSnapshotRecord,
        BrokerExecutionSnapshotRecord,
        BrokerCommissionSnapshotRecord,
    ]
    for item in types_to_check:
        for field in fields(item):
            lower = field.name.lower()
            assert not any(word in lower for word in forbidden)


def test_protocols_expose_expected_method_names() -> None:
    assert {"get_by_id", "list_accounts", "save_account"} <= set(BrokerAccountRepository.__dict__)
    assert {"get_by_id", "list_for_account", "save_sync_run"} <= set(
        BrokerSyncRunRepository.__dict__
    )
    assert {
        "list_position_snapshots",
        "list_cash_snapshots",
        "list_execution_snapshots",
        "list_commission_snapshots",
        "save_position_snapshot",
        "save_cash_snapshot",
        "save_execution_snapshot",
        "save_commission_snapshot",
    } <= set(BrokerSnapshotRepository.__dict__)
    assert {
        "get_report_by_id",
        "list_reports_for_sync_run",
        "list_differences_for_report",
        "save_report",
        "save_difference",
    } <= set(BrokerReconciliationRepository.__dict__)
    assert {"get_by_id", "list_for_account", "save_external_activity"} <= set(
        ExternalBrokerActivityRepository.__dict__
    )
    assert {"health", "commit", "rollback"} <= set(BrokerStorageUnitOfWork.__dict__)
    assert {"create_setup", "get_by_id", "get_latest"} <= set(
        PaperPortfolioSetupRepositoryProtocol.__dict__
    )


def test_paper_portfolio_setup_dto_uses_decimal_for_money() -> None:
    request = CreatePaperPortfolioSetupRequest(
        setup_id="setup-1",
        portfolio_name="Paper",
        base_currency="eur",
        starting_cash_amount=Decimal("1234.560000"),
        status="active",
        created_at=datetime.now(UTC),
        explanation_nl="Opzet.",
    )
    record = PaperPortfolioSetupRecord(
        setup_id=request.setup_id,
        portfolio_name=request.portfolio_name,
        base_currency=request.base_currency,
        starting_cash_amount=request.starting_cash_amount,
        paper_only=True,
        real_money_used=False,
        broker_order_created=False,
        live_trading_enabled=False,
        user_confirmed_paper_only=True,
        user_confirmed_no_real_money=True,
        user_confirmed_no_broker_order=True,
        status=request.status,
        created_at=request.created_at,
        updated_at=None,
        explanation_nl=request.explanation_nl,
    )
    assert isinstance(request.starting_cash_amount, Decimal)
    assert isinstance(record.starting_cash_amount, Decimal)


def test_result_contracts_behavior() -> None:
    write_result = StorageWriteResult(
        accepted=True,
        record_id="id-1",
        table_name="broker_accounts",
        audit_required=True,
        explanation_nl="Record geaccepteerd.",
    )
    read_result = StorageReadResult[object](
        found=False,
        record=None,
        table_name="broker_accounts",
        explanation_nl="Record niet gevonden.",
    )
    list_result = StorageListResult[object](
        records=(object(),),
        table_name="broker_accounts",
        explanation_nl="Lijst opgehaald.",
    )

    assert write_result.table_name
    assert write_result.explanation_nl
    assert read_result.found is False and read_result.record is None
    assert isinstance(list_result.records, tuple)


def test_repository_contracts_module_has_no_db_connection_markers() -> None:
    module_source = Path(
        "src/ai_trading_agent_storage/repository_contracts.py"
    ).read_text()

    forbidden_markers = (
        "create_engine",
        "sessionmaker",
        "DATABASE_URL",
        "os.environ",
        "getenv(",
    )
    for marker in forbidden_markers:
        assert marker not in module_source
