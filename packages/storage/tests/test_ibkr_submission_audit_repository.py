"""Task 134a — ibkr_submission_audit repository tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    IbkrSubmissionAuditEntry,
    SqlAlchemyIbkrSubmissionAuditRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)

_LATEST = "0052_ibkr_submission_lifecycle_audit_and_executions"


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


_BASE_TS = datetime(2026, 5, 26, 9, 0, tzinfo=UTC)


def _entry(
    *,
    draft_id: str = "draft-1",
    submitted_at: datetime | None = None,
    sent_to_account_id: str = "DU1234567",
    sent_account_mode: str = "paper",
    ibkr_perm_id: int | None = 100100,
    ibkr_order_id: int | None = 1,
    result: str = "placed",
    error_class: str | None = None,
    error_message_dutch: str | None = None,
) -> IbkrSubmissionAuditEntry:
    return IbkrSubmissionAuditEntry(
        action_draft_id=draft_id,
        submitted_at=submitted_at or _BASE_TS,
        sent_to_account_id=sent_to_account_id,
        sent_account_mode=sent_account_mode,
        ibkr_perm_id=ibkr_perm_id,
        ibkr_order_id=ibkr_order_id,
        contract_json={"symbol": "ASML", "exchange": "AEB"},
        order_json={
            "action": "BUY",
            "totalQuantity": "6",
            "orderType": "LMT",
            "lmtPrice": "638.72",
        },
        gateway_session_id="sess-1",
        result=result,
        error_class=error_class,
        error_message_dutch=error_message_dutch,
    )


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def test_append_returns_entry_with_autoincrement_id() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
        stored = repo.append(_entry())
        assert stored.id is not None
        assert stored.action_draft_id == "draft-1"
        assert stored.result == "placed"
        assert stored.contract_json["symbol"] == "ASML"


def test_list_for_account_orders_newest_first() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
        repo.append(
            _entry(draft_id="d-old", submitted_at=_BASE_TS, ibkr_perm_id=1)
        )
        repo.append(
            _entry(
                draft_id="d-new",
                submitted_at=_BASE_TS + timedelta(minutes=5),
                ibkr_perm_id=2,
            )
        )
        rows = repo.list_for_account(ibkr_account_id="DU1234567")
        assert [r.action_draft_id for r in rows] == ["d-new", "d-old"]


def test_list_for_account_filters_by_account() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
        repo.append(_entry(sent_to_account_id="A1", ibkr_perm_id=1))
        repo.append(
            _entry(
                draft_id="d2",
                sent_to_account_id="A2",
                ibkr_perm_id=2,
            )
        )
        assert len(repo.list_for_account(ibkr_account_id="A1")) == 1
        assert len(repo.list_for_account(ibkr_account_id="A2")) == 1


def test_list_for_draft_orders_chronologically() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
        repo.append(_entry(submitted_at=_BASE_TS, ibkr_perm_id=1))
        repo.append(
            _entry(
                submitted_at=_BASE_TS + timedelta(minutes=1),
                ibkr_perm_id=2,
            )
        )
        rows = repo.list_for_draft("draft-1")
        assert [r.ibkr_perm_id for r in rows] == [1, 2]


def test_appends_connection_lost_result() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrSubmissionAuditRepository(conn, _report())
        stored = repo.append(
            _entry(
                ibkr_perm_id=None,
                ibkr_order_id=None,
                result="connection_lost",
                error_class="TimeoutError",
                error_message_dutch="Verbinding met IBKR verbroken.",
            )
        )
        assert stored.result == "connection_lost"
        assert stored.ibkr_perm_id is None
        assert stored.error_message_dutch == "Verbinding met IBKR verbroken."


def test_invalid_result_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(result="garbage")


def test_invalid_account_mode_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(sent_account_mode="margin")
