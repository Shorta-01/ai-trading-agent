from datetime import datetime, UTC
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import MigrationReadinessReport, MigrationReadinessStatus
from ai_trading_agent_storage.repository_contracts import BrokerAccountRecord, BrokerSyncRunRecord
from ai_trading_agent_storage.sql_repositories import (
    SqlAlchemyBrokerAccountRepository,
    SqlAlchemyBrokerStorageUnitOfWork,
    SqlAlchemyBrokerSyncRunRepository,
    StoragePersistenceBlockedError,
    ensure_persistence_allowed,
)


def _report(allowed: bool) -> MigrationReadinessReport:
    return MigrationReadinessReport(MigrationReadinessStatus.MIGRATIONS_CURRENT if allowed else MigrationReadinessStatus.NOT_CONNECTED, allowed, allowed, True, "0006", "0006" if allowed else None, allowed, not allowed, "test")


def test_guard_blocks_when_not_allowed() -> None:
    with pytest.raises(StoragePersistenceBlockedError):
        ensure_persistence_allowed(_report(False))


def test_account_and_sync_roundtrip() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        account_repo = SqlAlchemyBrokerAccountRepository(conn, _report(True))
        account = BrokerAccountRecord("a1", "ibkr", None, "main", "paper", "connected", True, True, False, "broker", datetime.now(UTC), None, "ok")
        account_repo.save_account(account)
        assert account_repo.get_by_id("a1").found
        assert len(account_repo.list_accounts().records) == 1

        sync_repo = SqlAlchemyBrokerSyncRunRepository(conn, _report(True))
        run = BrokerSyncRunRecord("r1", "a1", "ibkr", "manual", "done", datetime.now(UTC), None, ("positions",), ("ibkr",), False, False, False, "sam", "help")
        sync_repo.save_sync_run(run)
        assert sync_repo.get_by_id("r1").found
        assert sync_repo.list_for_account("a1").records[0].planned_data_kinds_json == ("positions",)


def test_write_blocked() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        account_repo = SqlAlchemyBrokerAccountRepository(conn, _report(False))
        account = BrokerAccountRecord("a2", "ibkr", None, "main", "paper", "connected", True, True, False, "broker", datetime.now(UTC), None, "ok")
        with pytest.raises(StoragePersistenceBlockedError):
            account_repo.save_account(account)


def test_uow_health_and_noop_transaction_methods() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        uow = SqlAlchemyBrokerStorageUnitOfWork(conn, _report(True))
        assert uow.health().available
        uow.commit()
        uow.rollback()
