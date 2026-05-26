"""Task 135a — unmatched_execution_audit repository tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from ai_trading_agent_storage import (
    SqlAlchemyUnmatchedExecutionAuditRepository,
    UnmatchedExecutionAuditEntry,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)

_LATEST = "0053_reconciliation_audit_and_manual_review"
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


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def _entry(
    *,
    exec_id: str = "ibkr-exec-1",
    perm_id: int = 100100,
    account_id: str = "DU1234567",
    conid: str = "ASML.AS",
    side: str = "BUY",
    fill_price: Decimal = Decimal("638.72"),
    fill_quantity: Decimal = Decimal("6"),
    fill_time: datetime | None = None,
    event_at: datetime | None = None,
    raw: dict[str, object] | None = None,
    resolution_status: str = "unresolved",
) -> UnmatchedExecutionAuditEntry:
    return UnmatchedExecutionAuditEntry(
        event_at=event_at or _BASE_TS,
        ibkr_perm_id=perm_id,
        ibkr_exec_id=exec_id,
        account_id=account_id,
        conid=conid,
        side=side,
        fill_price_local=fill_price,
        fill_quantity=fill_quantity,
        fill_time=fill_time or _BASE_TS,
        raw_execution_json=raw or {"perm_id": perm_id, "side": side},
        resolution_status=resolution_status,
    )


def test_append_returns_entry_with_autoincrement_id() -> None:
    with _conn() as conn:
        repo = SqlAlchemyUnmatchedExecutionAuditRepository(conn, _report())
        stored = repo.append(_entry())
        assert stored.id is not None
        assert stored.ibkr_exec_id == "ibkr-exec-1"
        assert stored.resolution_status == "unresolved"


def test_unique_exec_id_rejects_duplicate() -> None:
    with _conn() as conn:
        repo = SqlAlchemyUnmatchedExecutionAuditRepository(conn, _report())
        repo.append(_entry(exec_id="dup-1"))
        with pytest.raises(IntegrityError):
            repo.append(_entry(exec_id="dup-1", perm_id=999999))


def test_get_by_exec_id_returns_row_or_none() -> None:
    with _conn() as conn:
        repo = SqlAlchemyUnmatchedExecutionAuditRepository(conn, _report())
        repo.append(_entry(exec_id="known"))
        found = repo.get_by_exec_id("known")
        missing = repo.get_by_exec_id("unknown")
        assert found is not None
        assert found.ibkr_exec_id == "known"
        assert missing is None


def test_get_by_exec_id_preserves_decimal_precision() -> None:
    with _conn() as conn:
        repo = SqlAlchemyUnmatchedExecutionAuditRepository(conn, _report())
        repo.append(
            _entry(
                exec_id="prec-1",
                fill_price=Decimal("123.45678901"),
                fill_quantity=Decimal("0.12345678"),
            )
        )
        fetched = repo.get_by_exec_id("prec-1")
        assert fetched is not None
        assert fetched.fill_price_local == Decimal("123.45678901")
        assert fetched.fill_quantity == Decimal("0.12345678")


def test_list_unresolved_for_account_orders_by_fill_time_desc() -> None:
    with _conn() as conn:
        repo = SqlAlchemyUnmatchedExecutionAuditRepository(conn, _report())
        repo.append(
            _entry(exec_id="e-old", fill_time=_BASE_TS, perm_id=1)
        )
        repo.append(
            _entry(
                exec_id="e-new",
                fill_time=_BASE_TS + timedelta(minutes=5),
                perm_id=2,
            )
        )
        rows = repo.list_unresolved_for_account("DU1234567")
        assert [r.ibkr_exec_id for r in rows] == ["e-new", "e-old"]


def test_list_unresolved_excludes_resolved_rows() -> None:
    with _conn() as conn:
        repo = SqlAlchemyUnmatchedExecutionAuditRepository(conn, _report())
        repo.append(_entry(exec_id="e-unres", perm_id=1))
        repo.append(
            _entry(
                exec_id="e-matched",
                perm_id=2,
                resolution_status="manually_matched",
            )
        )
        repo.append(
            _entry(
                exec_id="e-ignored",
                perm_id=3,
                resolution_status="ignored",
            )
        )
        rows = repo.list_unresolved_for_account("DU1234567")
        assert {r.ibkr_exec_id for r in rows} == {"e-unres"}


def test_list_unresolved_filters_by_account() -> None:
    with _conn() as conn:
        repo = SqlAlchemyUnmatchedExecutionAuditRepository(conn, _report())
        repo.append(_entry(exec_id="e-a", account_id="DU1111111", perm_id=1))
        repo.append(_entry(exec_id="e-b", account_id="DU2222222", perm_id=2))
        rows_a = repo.list_unresolved_for_account("DU1111111")
        rows_b = repo.list_unresolved_for_account("DU2222222")
        assert [r.ibkr_exec_id for r in rows_a] == ["e-a"]
        assert [r.ibkr_exec_id for r in rows_b] == ["e-b"]


def test_invalid_side_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(side="LONG")


def test_zero_fill_price_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(fill_price=Decimal("0"))


def test_zero_fill_quantity_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(fill_quantity=Decimal("0"))


def test_invalid_resolution_status_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(resolution_status="closed")


def test_empty_exec_id_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(exec_id="")
