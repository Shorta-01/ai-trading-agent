"""Task 134a — ibkr_executions repository tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from ai_trading_agent_storage import (
    IbkrExecutionEntry,
    SqlAlchemyIbkrExecutionsRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)

_LATEST = "0052_ibkr_submission_lifecycle_audit_and_executions"
_BASE_TS = datetime(2026, 5, 26, 9, 0, tzinfo=UTC)


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id=_LATEST,
        database_revision_id=_LATEST,
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


def _execution(
    *,
    exec_id: str = "exec-1",
    perm_id: int = 100100,
    draft_id: str = "draft-1",
    account_id: str = "DU1234567",
    conid: str = "ASML.AS",
    side: str = "BUY",
    fill_price: Decimal = Decimal("638.72"),
    fill_quantity: Decimal = Decimal("6"),
    fill_time: datetime | None = None,
    commission: Decimal = Decimal("1.50"),
) -> IbkrExecutionEntry:
    return IbkrExecutionEntry(
        ibkr_exec_id=exec_id,
        ibkr_perm_id=perm_id,
        action_draft_id=draft_id,
        account_id=account_id,
        conid=conid,
        side=side,
        fill_price_local=fill_price,
        fill_quantity=fill_quantity,
        fill_time=fill_time or _BASE_TS,
        commission=commission,
        commission_currency="EUR",
        exchange="AEB",
    )


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def test_append_returns_entry_with_autoincrement_id() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrExecutionsRepository(conn, _report())
        stored = repo.append(_execution())
        assert stored.id is not None
        assert stored.ibkr_exec_id == "exec-1"


def test_unique_exec_id_rejects_duplicate() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrExecutionsRepository(conn, _report())
        repo.append(_execution(exec_id="exec-dup"))
        with pytest.raises(IntegrityError):
            repo.append(_execution(exec_id="exec-dup"))


def test_get_by_exec_id_roundtrips() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrExecutionsRepository(conn, _report())
        repo.append(_execution())
        fetched = repo.get_by_exec_id("exec-1")
        assert fetched is not None
        assert fetched.fill_price_local == Decimal("638.72000000")
        assert fetched.fill_quantity == Decimal("6")
        assert fetched.commission == Decimal("1.50000000")


def test_list_for_account_conid_filters() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrExecutionsRepository(conn, _report())
        repo.append(_execution(exec_id="e-asml", conid="ASML.AS"))
        repo.append(_execution(exec_id="e-shel", conid="SHEL.L"))
        rows = repo.list_for_account_conid(
            account_id="DU1234567", conid="ASML.AS"
        )
        assert len(rows) == 1
        assert rows[0].conid == "ASML.AS"


def test_list_for_account_conid_orders_newest_first() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrExecutionsRepository(conn, _report())
        repo.append(_execution(exec_id="e1", fill_time=_BASE_TS))
        repo.append(
            _execution(
                exec_id="e2", fill_time=_BASE_TS + timedelta(minutes=1)
            )
        )
        rows = repo.list_for_account_conid(
            account_id="DU1234567", conid="ASML.AS"
        )
        assert [r.ibkr_exec_id for r in rows] == ["e2", "e1"]


def test_list_for_draft_returns_partial_fills() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrExecutionsRepository(conn, _report())
        repo.append(
            _execution(
                exec_id="e1",
                fill_quantity=Decimal("3"),
                fill_time=_BASE_TS,
            )
        )
        repo.append(
            _execution(
                exec_id="e2",
                fill_quantity=Decimal("3"),
                fill_time=_BASE_TS + timedelta(seconds=2),
            )
        )
        rows = repo.list_for_draft("draft-1")
        assert len(rows) == 2
        assert sum(r.fill_quantity for r in rows) == Decimal("6")


def test_invalid_side_rejected_at_dataclass() -> None:
    with pytest.raises(ValueError):
        _execution(side="HOLD")


def test_zero_quantity_rejected_at_dataclass() -> None:
    with pytest.raises(ValueError):
        _execution(fill_quantity=Decimal("0"))


def test_negative_commission_rejected_at_dataclass() -> None:
    with pytest.raises(ValueError):
        _execution(commission=Decimal("-1"))
