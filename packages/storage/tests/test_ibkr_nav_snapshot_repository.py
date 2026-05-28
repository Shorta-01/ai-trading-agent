"""Tests for the IBKR NAV-snapshot repository (drawdown history, T-045 §2)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine

from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from ai_trading_agent_storage.repository_contracts import IbkrNavSnapshotRecord
from ai_trading_agent_storage.sql_repositories import (
    SqlAlchemyIbkrSyncSnapshotRepository,
)

_NOW = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0055_runtime_config",
        database_revision_id="0055_runtime_config",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


def _nav(account: str, value: str, recorded_at: datetime) -> IbkrNavSnapshotRecord:
    return IbkrNavSnapshotRecord(
        snapshot_id=f"{account}-{recorded_at.isoformat()}",
        ibkr_account_id=account,
        base_currency="EUR",
        nav_value=Decimal(value),
        recorded_at=recorded_at,
        stored_at=recorded_at,
    )


def test_save_and_list_since_filters_by_account_and_time() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyIbkrSyncSnapshotRepository(conn, _report())

        repo.save_ibkr_nav_snapshot(_nav("DU1", "50000", _NOW - timedelta(days=25)))
        repo.save_ibkr_nav_snapshot(_nav("DU1", "55000", _NOW - timedelta(days=10)))
        repo.save_ibkr_nav_snapshot(_nav("DU1", "52000", _NOW - timedelta(days=1)))
        repo.save_ibkr_nav_snapshot(_nav("DU2", "99000", _NOW - timedelta(days=1)))

        out = repo.list_ibkr_nav_snapshots_since(
            ibkr_account_id="DU1", since=_NOW - timedelta(days=20)
        )

    assert [r.nav_value for r in out] == [Decimal("55000"), Decimal("52000")]
    assert all(r.ibkr_account_id == "DU1" for r in out)


def test_list_since_empty_when_no_history() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyIbkrSyncSnapshotRepository(conn, _report())
        out = repo.list_ibkr_nav_snapshots_since(
            ibkr_account_id="DU1", since=_NOW - timedelta(days=20)
        )
    assert out == []
