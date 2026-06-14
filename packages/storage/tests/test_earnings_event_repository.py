"""Tests for ``SqlAlchemyEarningsEventRepository`` (V1.2 §AI)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, text

from ai_trading_agent_storage import (
    EarningsEventRecord,
    SaveEarningsEventRequest,
    SqlAlchemyEarningsEventRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)


@pytest.fixture
def connection():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0080_dashboard_query_indexes')"
            )
        )
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
    finally:
        trans.rollback()
        conn.close()
        engine.dispose()


def _readiness(persistence_allowed: bool = True) -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0080_dashboard_query_indexes",
        database_revision_id="0080_dashboard_query_indexes",
        persistence_allowed=persistence_allowed,
        blocks_runtime_writes=False,
        explanation_nl="Test readiness — migration up-to-date.",
    )


def _request(
    *,
    earnings_event_id: str = "ev-1",
    symbol: str = "AAPL",
    event_date: date = date(2026, 7, 15),
    status: str = "confirmed",
) -> SaveEarningsEventRequest:
    return SaveEarningsEventRequest(
        earnings_event_id=earnings_event_id,
        symbol=symbol,
        ibkr_conid="1",
        event_date=event_date,
        status=status,
        source="eodhd",
        fetched_at=datetime(2026, 6, 12, 6, 0, tzinfo=UTC),
        raw_json={"eps_estimate": "1.45"},
    )


def test_record_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="status must be"):
        EarningsEventRecord(
            earnings_event_id="ev-1",
            symbol="AAPL",
            ibkr_conid=None,
            event_date=date(2026, 7, 15),
            status="bogus",
            source="eodhd",
            fetched_at=datetime(2026, 6, 12, tzinfo=UTC),
            raw_json=None,
        )


def test_upsert_event_inserts_new_row(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyEarningsEventRepository(connection, _readiness())
    result = repo.upsert_event(_request())
    assert result.accepted is True
    assert result.record_id == "ev-1"


def test_upsert_event_replaces_existing_row(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyEarningsEventRepository(connection, _readiness())
    repo.upsert_event(_request(status="estimated"))
    repo.upsert_event(_request(earnings_event_id="ev-2", status="confirmed"))
    upcoming = repo.list_upcoming(
        from_date=date(2026, 6, 12), to_date=date(2026, 12, 31)
    )
    assert len(upcoming.records) == 1
    assert upcoming.records[0].earnings_event_id == "ev-2"
    assert upcoming.records[0].status == "confirmed"


def test_list_upcoming_filters_by_date_and_excludes_past(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyEarningsEventRepository(connection, _readiness())
    repo.upsert_event(
        _request(earnings_event_id="ev-1", symbol="A", event_date=date(2026, 7, 15))
    )
    repo.upsert_event(
        _request(earnings_event_id="ev-2", symbol="B", event_date=date(2026, 8, 15))
    )
    repo.upsert_event(
        _request(
            earnings_event_id="ev-3",
            symbol="C",
            event_date=date(2026, 5, 1),
            status="past",
        )
    )
    repo.upsert_event(
        _request(earnings_event_id="ev-4", symbol="D", event_date=date(2027, 1, 5))
    )

    upcoming = repo.list_upcoming(
        from_date=date(2026, 6, 1), to_date=date(2026, 12, 31)
    )
    symbols = [rec.symbol for rec in upcoming.records]
    # ev-3 is past status → excluded; ev-4 is outside window → excluded.
    assert symbols == ["A", "B"]


def test_get_next_for_symbols_picks_nearest_future_date(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyEarningsEventRepository(connection, _readiness())
    repo.upsert_event(
        _request(earnings_event_id="ev-1", symbol="AAPL", event_date=date(2026, 7, 15))
    )
    repo.upsert_event(
        _request(earnings_event_id="ev-2", symbol="AAPL", event_date=date(2026, 10, 15))
    )
    repo.upsert_event(
        _request(earnings_event_id="ev-3", symbol="MSFT", event_date=date(2026, 8, 1))
    )
    next_for = repo.get_next_for_symbols(
        symbols=("AAPL", "MSFT", "NEW"), today=date(2026, 6, 12)
    )
    assert next_for["AAPL"] == date(2026, 7, 15)
    assert next_for["MSFT"] == date(2026, 8, 1)
    assert next_for["NEW"] is None  # no rows for this symbol


def test_get_next_for_symbols_skips_past_events(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyEarningsEventRepository(connection, _readiness())
    repo.upsert_event(
        _request(earnings_event_id="ev-1", symbol="AAPL", event_date=date(2026, 5, 1))
    )
    next_for = repo.get_next_for_symbols(
        symbols=("AAPL",), today=date(2026, 6, 12)
    )
    assert next_for["AAPL"] is None


def test_get_next_for_symbols_handles_empty_input(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyEarningsEventRepository(connection, _readiness())
    assert repo.get_next_for_symbols(symbols=(), today=date(2026, 6, 12)) == {}
