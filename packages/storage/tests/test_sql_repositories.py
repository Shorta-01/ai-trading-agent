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
)
from ai_trading_agent_storage.sql_repositories import (
    SqlAlchemyBrokerAccountRepository,
    SqlAlchemyBrokerStorageUnitOfWork,
    SqlAlchemyBrokerSyncRunRepository,
    SqlAlchemyPaperPortfolioSetupRepository,
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
        latest_expected_revision_id="0006",
        database_revision_id="0006" if allowed else None,
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
