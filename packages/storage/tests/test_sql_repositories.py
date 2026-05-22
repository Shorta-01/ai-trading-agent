from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from ai_trading_agent_storage.repository_contracts import (
    BrokerAccountRecord,
    BrokerSyncRunRecord,
    CreatePaperPortfolioSetupRequest,
    CreateSystemEventRequest,
    IbkrAccountCashSnapshotRecord,
    IbkrExecutionSnapshotRecord,
    IbkrOpenOrderSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
    SaveTradingSettingsRequest,
)
from ai_trading_agent_storage.sql_repositories import (
    SqlAlchemyBrokerAccountRepository,
    SqlAlchemyBrokerStorageUnitOfWork,
    SqlAlchemyBrokerSyncRunRepository,
    SqlAlchemyIbkrSyncSnapshotRepository,
    SqlAlchemyPaperPortfolioSetupRepository,
    SqlAlchemySystemEventRepository,
    SqlAlchemyTradingSettingsRepository,
    StoragePersistenceBlockedError,
    ensure_persistence_allowed,
)


def _report(allowed: bool) -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=(
            MigrationReadinessStatus.MIGRATIONS_CURRENT
            if allowed
            else MigrationReadinessStatus.NOT_CONNECTED
        ),
        database_connected=allowed,
        migrations_checked_against_database=allowed,
        offline_inventory_valid=True,
        latest_expected_revision_id="0011",
        database_revision_id="0011" if allowed else None,
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


def test_guard_blocks_when_not_allowed() -> None:
    with pytest.raises(StoragePersistenceBlockedError):
        ensure_persistence_allowed(_report(False))


def test_account_and_sync_roundtrip() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        account_repo = SqlAlchemyBrokerAccountRepository(conn, _report(True))
        account = BrokerAccountRecord(
            "a1",
            "ibkr",
            None,
            "main",
            "paper",
            "connected",
            True,
            True,
            False,
            "broker",
            datetime.now(UTC),
            None,
            "ok",
        )
        account_repo.save_account(account)
        assert account_repo.get_by_id("a1").found
        assert len(account_repo.list_accounts().records) == 1

        sync_repo = SqlAlchemyBrokerSyncRunRepository(conn, _report(True))
        run = BrokerSyncRunRecord(
            "r1",
            "a1",
            "ibkr",
            "manual",
            "done",
            datetime.now(UTC),
            None,
            ("positions",),
            ("ibkr",),
            False,
            False,
            False,
            "sam",
            "help",
            None,
            None,
        )
        sync_repo.save_sync_run(run)
        assert sync_repo.get_by_id("r1").found
        assert sync_repo.list_for_account("a1").records[0].planned_data_kinds_json == ("positions",)


def test_write_blocked() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        account_repo = SqlAlchemyBrokerAccountRepository(conn, _report(False))
        account = BrokerAccountRecord(
            "a2",
            "ibkr",
            None,
            "main",
            "paper",
            "connected",
            True,
            True,
            False,
            "broker",
            datetime.now(UTC),
            None,
            "ok",
        )
        with pytest.raises(StoragePersistenceBlockedError):
            account_repo.save_account(account)


def test_uow_health_and_noop_transaction_methods() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        uow = SqlAlchemyBrokerStorageUnitOfWork(conn, _report(True))
        assert uow.health().available
        uow.commit()
        uow.rollback()


def test_paper_setup_roundtrip_decimal_and_latest() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyPaperPortfolioSetupRepository(conn, _report(True))
        request = CreatePaperPortfolioSetupRequest(
            setup_id="setup-1",
            portfolio_name="Paper Start",
            base_currency="eur",
            starting_cash_amount=Decimal("1500.250000"),
            status="active",
            created_at=datetime.now(UTC),
            explanation_nl="Eerste papieren portfolio-opzet.",
        )

        write_result = repo.create_setup(request)
        assert write_result.accepted
        by_id_result = repo.get_by_id("setup-1")
        assert by_id_result.found
        assert by_id_result.record is not None
        assert isinstance(by_id_result.record.starting_cash_amount, Decimal)
        assert by_id_result.record.starting_cash_amount == Decimal("1500.250000")

        latest = repo.get_latest()
        assert latest.found
        assert latest.record is not None
        assert latest.record.setup_id == "setup-1"


def test_paper_setup_missing_record_returns_not_found() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyPaperPortfolioSetupRepository(conn, _report(True))
        assert repo.get_by_id("missing").found is False
        assert repo.get_latest().found is False


def test_paper_setup_write_blocked_and_allowed_by_readiness() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        blocked = SqlAlchemyPaperPortfolioSetupRepository(conn, _report(False))
        request = CreatePaperPortfolioSetupRequest(
            setup_id="setup-blocked",
            portfolio_name="Blocked",
            base_currency="eur",
            starting_cash_amount=Decimal("100.00"),
            status="active",
            created_at=datetime.now(UTC),
            explanation_nl="Geblokkeerde schrijfactie test.",
        )
        with pytest.raises(StoragePersistenceBlockedError):
            blocked.create_setup(request)

        allowed = SqlAlchemyPaperPortfolioSetupRepository(conn, _report(True))
        result = allowed.create_setup(request)
        assert result.accepted is True


def test_paper_setup_duplicate_and_invalid_writes_surface() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyPaperPortfolioSetupRepository(conn, _report(True))
        base_request = CreatePaperPortfolioSetupRequest(
            setup_id="setup-dup",
            portfolio_name="Dup",
            base_currency="eur",
            starting_cash_amount=Decimal("100.00"),
            status="active",
            created_at=datetime.now(UTC),
            explanation_nl="Duplicaat test.",
        )
        repo.create_setup(base_request)
        with pytest.raises(IntegrityError):
            repo.create_setup(base_request)

        invalid_currency = CreatePaperPortfolioSetupRequest(
            setup_id="setup-invalid",
            portfolio_name="Invalid",
            base_currency="usd",
            starting_cash_amount=Decimal("100.00"),
            status="active",
            created_at=datetime.now(UTC),
            explanation_nl="Constraint test.",
        )
        with pytest.raises(IntegrityError):
            repo.create_setup(invalid_currency)


def test_system_event_create_read_list_and_flags() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemySystemEventRepository(conn, _report(True))
        request = CreateSystemEventRequest(
            system_event_id="se-1",
            created_at=datetime.now(UTC),
            severity="error",
            category="storage",
            source_service="api",
            source_component="startup",
            event_code="storage_blocked",
            title_nl="Opslag geblokkeerd",
            message_nl="Schrijven is geblokkeerd.",
            help_nl="Controleer migraties.",
            technical_summary="alembic mismatch",
            redacted_details_json={"database_url": "***"},
            stack_trace_redacted="trace",
            related_entity_type="migration",
            related_entity_id="0007",
            blocks_suggestions=True,
            blocks_writes=True,
            blocks_ai_explanation=False,
            status="open",
            explanation_nl="Systeemmelding geregistreerd.",
        )
        repo.create_event(request)
        by_id = repo.get_by_id("se-1")
        assert by_id.found
        assert by_id.record is not None
        assert by_id.record.severity == "error"
        assert by_id.record.category == "storage"
        assert by_id.record.status == "open"
        assert by_id.record.blocks_suggestions is True
        assert by_id.record.blocks_writes is True
        assert by_id.record.redacted_details_json == {"database_url": "***"}

        second = CreateSystemEventRequest(
            **{**request.__dict__, "system_event_id": "se-2", "status": "resolved"}
        )
        repo.create_event(second)
        open_events = repo.list_open_events()
        assert [item.system_event_id for item in open_events.records] == ["se-1"]


def test_system_event_write_blocked_and_missing_and_no_delete() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        blocked_repo = SqlAlchemySystemEventRepository(conn, _report(False))
        request = CreateSystemEventRequest(
            system_event_id="se-blocked",
            created_at=datetime.now(UTC),
            severity="warning",
            category="api",
            source_service="api",
            source_component="guard",
            event_code="blocked",
            title_nl="Geblokkeerd",
            message_nl="Geen write",
            help_nl="Wacht",
            technical_summary=None,
            redacted_details_json=None,
            stack_trace_redacted=None,
            related_entity_type=None,
            related_entity_id=None,
            blocks_suggestions=False,
            blocks_writes=False,
            blocks_ai_explanation=False,
            status="open",
            explanation_nl="Test",
        )
        with pytest.raises(StoragePersistenceBlockedError):
            blocked_repo.create_event(request)

        allowed_repo = SqlAlchemySystemEventRepository(conn, _report(True))
        assert allowed_repo.get_by_id("missing").found is False
        assert allowed_repo.mark_resolved("missing").accepted is False
        assert allowed_repo.mark_archived("missing").accepted is False
        assert hasattr(allowed_repo, "delete") is False


def test_system_event_resolve_and_archive_hide_from_open_list() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemySystemEventRepository(conn, _report(True))
        create = CreateSystemEventRequest(
            system_event_id="se-open",
            created_at=datetime.now(UTC),
            severity="warning",
            category="api",
            source_service="api",
            source_component="events",
            event_code="open_event",
            title_nl="Open event",
            message_nl="Open event message",
            help_nl="Help",
            technical_summary=None,
            redacted_details_json=None,
            stack_trace_redacted=None,
            related_entity_type=None,
            related_entity_id=None,
            blocks_suggestions=False,
            blocks_writes=False,
            blocks_ai_explanation=False,
            status="open",
            explanation_nl="Open",
        )
        repo.create_event(create)
        assert [item.system_event_id for item in repo.list_open_events().records] == ["se-open"]

        resolved = repo.mark_resolved("se-open", reason_nl="Handmatig opgelost")
        assert resolved.accepted is True
        after_resolve = repo.get_by_id("se-open")
        assert after_resolve.record is not None
        assert after_resolve.record.status == "resolved"
        assert after_resolve.record.resolved_at is not None
        assert repo.list_open_events().records == ()

        second = CreateSystemEventRequest(**{**create.__dict__, "system_event_id": "se-open-2"})
        repo.create_event(second)
        archived = repo.mark_archived("se-open-2", reason_nl="Niet meer relevant")
        assert archived.accepted is True
        after_archive = repo.get_by_id("se-open-2")
        assert after_archive.record is not None
        assert after_archive.record.status == "archived"
        assert after_archive.record.archived_at is not None
        assert repo.list_open_events().records == ()


def test_ibkr_sync_repository_roundtrip_and_lists() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    now = datetime.now(UTC)
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyIbkrSyncSnapshotRepository(conn, _report(True))
        run = IbkrSyncRunRecord(
            sync_run_id="sync-1",
            started_at=now,
            completed_at=now,
            provider_code="ibkr",
            provider_environment="paper",
            account_mode="paper",
            readonly=True,
            status="completed",
            account_summary_status="ok",
            positions_status="ok",
            open_orders_status="ok",
            executions_status="ok",
            positions_count=1,
            cash_values_count=1,
            open_orders_count=1,
            executions_count=1,
            status_nl=None,
            next_step_nl=None,
            help_nl=None,
            actions_allowed=False,
            order_submission_allowed=False,
            order_modification_allowed=False,
            order_cancellation_allowed=False,
            suggestions_allowed=False,
            stored_at=now,
        )
        repo.save_ibkr_sync_run(run)
        loaded_run = repo.get_ibkr_sync_run("sync-1")
        assert loaded_run is not None
        assert loaded_run.sync_run_id == run.sync_run_id
        assert loaded_run.actions_allowed is False
        assert repo.get_ibkr_sync_run("missing") is None
        latest_run = repo.get_latest_ibkr_sync_run()
        assert latest_run is not None
        assert latest_run.sync_run_id == run.sync_run_id
        assert len(repo.list_ibkr_sync_runs(limit=5)) == 1

        cash = IbkrAccountCashSnapshotRecord(
            "c1", "sync-1", None, "EUR", Decimal("1.2"), None, None, now, now
        )
        pos = IbkrPositionSnapshotRecord(
            "p1",
            "sync-1",
            None,
            None,
            "AAPL",
            "STK",
            "USD",
            None,
            None,
            Decimal("2"),
            None,
            now,
            now,
        )
        order = IbkrOpenOrderSnapshotRecord(
            "o1", "sync-1", None, 1, None, None, None, "AAPL", "STK", "USD",
            None, None, "BUY", "LMT", Decimal("1"), None, None, None, "Submitted",
            Decimal("0"), Decimal("1"), None, None, None, now, now
        )
        exe = IbkrExecutionSnapshotRecord(
            "e1", "sync-1", None, "exec-1", None, None, "AAPL", "STK", "USD",
            None, None, "BUY", Decimal("1"), Decimal("10"), now, None, None,
            None, None, now, now
        )

        repo.save_ibkr_account_cash_snapshots("sync-1", [cash])
        repo.save_ibkr_position_snapshots("sync-1", [pos])
        repo.save_ibkr_open_order_snapshots("sync-1", [order])
        repo.save_ibkr_execution_snapshots("sync-1", [exe])

        loaded_cash = repo.list_ibkr_account_cash_snapshots("sync-1")
        loaded_positions = repo.list_ibkr_position_snapshots("sync-1")
        loaded_orders = repo.list_ibkr_open_order_snapshots("sync-1")
        loaded_executions = repo.list_ibkr_execution_snapshots("sync-1")
        assert loaded_cash[0].snapshot_id == "c1"
        assert isinstance(loaded_cash[0].cash, Decimal)
        assert loaded_cash[0].available_funds is None
        assert loaded_positions[0].snapshot_id == "p1"
        assert isinstance(loaded_positions[0].quantity, Decimal)
        assert loaded_orders[0].snapshot_id == "o1"
        assert isinstance(loaded_orders[0].quantity, Decimal)
        assert loaded_executions[0].snapshot_id == "e1"
        assert isinstance(loaded_executions[0].price, Decimal)


def test_trading_settings_save_read_update_and_not_found() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyTradingSettingsRepository(conn, _report(True))
        missing = repo.get_settings("missing")
        assert missing.found is False

        first = SaveTradingSettingsRequest(
            settings_id="default",
            allowed_universe={"max_pct_per_sector": "10"},
            user_strategy={"max_pct_per_positie": "5"},
            source="instellingen",
            status="actief",
            explanation_nl="Eerste instellingen opgeslagen.",
            updated_at=datetime.now(UTC),
        )
        repo.save_settings(first)
        saved = repo.get_settings()
        assert saved.found is True
        assert saved.record is not None
        assert saved.record.version == 1
        assert saved.record.allowed_universe["max_pct_per_sector"] == "10"
        assert saved.record.user_strategy["max_pct_per_positie"] == "5"

        second = SaveTradingSettingsRequest(
            settings_id="default",
            allowed_universe={"max_pct_per_sector": "15"},
            user_strategy={"max_pct_per_positie": "6"},
            source="instellingen",
            status="actief",
            explanation_nl="Instellingen bijgewerkt.",
            updated_at=datetime.now(UTC),
        )
        repo.save_settings(second)
        updated = repo.get_settings()
        assert updated.record is not None
        assert updated.record.version == 2
        assert updated.record.allowed_universe["max_pct_per_sector"] == "15"


def test_trading_settings_write_blocked_until_readiness_safe() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        blocked = SqlAlchemyTradingSettingsRepository(conn, _report(False))
        with pytest.raises(StoragePersistenceBlockedError):
            blocked.save_settings(
                SaveTradingSettingsRequest(
                    settings_id="default",
                    allowed_universe={"a": "10"},
                    user_strategy={"b": "5"},
                    source="instellingen",
                    status="actief",
                    explanation_nl="Geblokkeerd.",
                    updated_at=datetime.now(UTC),
                )
            )
