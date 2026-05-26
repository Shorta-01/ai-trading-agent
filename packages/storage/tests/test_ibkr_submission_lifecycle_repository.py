"""Task 134a — ibkr_submission_lifecycle repository tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    IbkrSubmissionLifecycleEntry,
    SqlAlchemyIbkrSubmissionLifecycleRepository,
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


def _entry(
    *,
    draft_id: str = "draft-1",
    event_at: datetime | None = None,
    perm_id: int = 100100,
    event_type: str = "status_change",
    from_status: str | None = "submitted",
    to_status: str | None = "accepted",
    raw_status: str | None = "Submitted",
    fill_price: Decimal | None = None,
    fill_quantity: Decimal | None = None,
    commission: Decimal | None = None,
    commission_currency: str | None = None,
) -> IbkrSubmissionLifecycleEntry:
    return IbkrSubmissionLifecycleEntry(
        action_draft_id=draft_id,
        event_at=event_at or _BASE_TS,
        ibkr_perm_id=perm_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        ibkr_raw_status=raw_status,
        fill_price_local=fill_price,
        fill_quantity=fill_quantity,
        commission=commission,
        commission_currency=commission_currency,
        raw_callback_json={"orderStatus": {"status": raw_status or ""}},
    )


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def test_append_records_status_change_with_autoincrement() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrSubmissionLifecycleRepository(
            conn, _report()
        )
        stored = repo.append(_entry())
        assert stored.id is not None
        assert stored.event_type == "status_change"
        assert stored.from_status == "submitted"
        assert stored.to_status == "accepted"


def test_list_for_draft_orders_chronologically() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrSubmissionLifecycleRepository(
            conn, _report()
        )
        repo.append(
            _entry(event_at=_BASE_TS, from_status="submitted", to_status="accepted")
        )
        repo.append(
            _entry(
                event_at=_BASE_TS + timedelta(seconds=2),
                from_status="accepted",
                to_status="working",
                raw_status="PreSubmitted",
            )
        )
        repo.append(
            _entry(
                event_at=_BASE_TS + timedelta(seconds=5),
                event_type="fill",
                from_status="working",
                to_status="filled",
                raw_status="Filled",
                fill_price=Decimal("638.72"),
                fill_quantity=Decimal("6"),
            )
        )
        rows = repo.list_for_draft("draft-1")
        assert [r.to_status for r in rows] == ["accepted", "working", "filled"]
        assert rows[-1].fill_price_local == Decimal("638.72000000")


def test_list_for_perm_id_filters_correctly() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrSubmissionLifecycleRepository(
            conn, _report()
        )
        repo.append(_entry(perm_id=1))
        repo.append(_entry(perm_id=2, draft_id="draft-2"))
        rows = repo.list_for_perm_id(1)
        assert len(rows) == 1
        assert rows[0].ibkr_perm_id == 1


def test_fill_event_carries_decimal_fields() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrSubmissionLifecycleRepository(
            conn, _report()
        )
        stored = repo.append(
            _entry(
                event_type="fill",
                from_status="working",
                to_status="filled",
                raw_status="Filled",
                fill_price=Decimal("638.72000000"),
                fill_quantity=Decimal("6"),
            )
        )
        assert stored.fill_price_local == Decimal("638.72000000")
        assert stored.fill_quantity == Decimal("6")


def test_commission_report_event_carries_currency() -> None:
    with _conn() as conn:
        repo = SqlAlchemyIbkrSubmissionLifecycleRepository(
            conn, _report()
        )
        stored = repo.append(
            _entry(
                event_type="commission_report",
                from_status=None,
                to_status=None,
                raw_status=None,
                commission=Decimal("1.50"),
                commission_currency="EUR",
            )
        )
        assert stored.commission == Decimal("1.50000000")
        assert stored.commission_currency == "EUR"


def test_invalid_event_type_rejected_at_dataclass() -> None:
    with pytest.raises(ValueError):
        _entry(event_type="status_chnage")  # typo


def test_invalid_status_rejected_at_dataclass() -> None:
    with pytest.raises(ValueError):
        _entry(to_status="not_a_real_status")
