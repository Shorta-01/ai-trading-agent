"""Tests for ``refresh_earnings_calendar`` (V1.2 §AJ)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from ai_trading_agent_storage import SqlAlchemyEarningsEventRepository
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine, text

from portfolio_outlook_api.earnings_sync import (
    EarningsRefreshSummary,
    refresh_earnings_calendar,
)
from portfolio_outlook_api.eodhd_client import EodhdEarningsEvent


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
                "('0072_earnings_events')"
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


def _readiness() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0072_earnings_events",
        database_revision_id="0072_earnings_events",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="ok",
    )


class _StubProvider:
    """Records calls and returns pre-canned events."""

    def __init__(self, events: list[EodhdEarningsEvent]) -> None:
        self._events = events
        self.calls: list[tuple[tuple[str, ...], date, date]] = []

    def fetch_earnings_calendar(
        self,
        *,
        symbols: tuple[str, ...],
        from_date: date,
        to_date: date,
    ) -> list[EodhdEarningsEvent]:
        self.calls.append((symbols, from_date, to_date))
        return list(self._events)


class _FailingProvider:
    """Always raises to exercise the boundary catch."""

    def fetch_earnings_calendar(
        self,
        *,
        symbols: tuple[str, ...],
        from_date: date,
        to_date: date,
    ) -> list[EodhdEarningsEvent]:
        raise RuntimeError("eodhd_quota_exhausted")


_NOW = datetime(2026, 6, 12, 6, 0, tzinfo=UTC)
_TODAY = _NOW.date()


def test_refresh_returns_zero_summary_on_empty_input(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyEarningsEventRepository(connection, _readiness())
    provider = _StubProvider([])
    summary = refresh_earnings_calendar(
        provider=provider,
        repository=repo,
        symbols=[],
        today=_TODAY,
        window_days=21,
        source="eodhd",
        fetched_at=_NOW,
    )
    assert summary == EarningsRefreshSummary(
        fetched_count=0,
        upserted_count=0,
        symbols_requested=0,
        window_days=21,
        error_text=None,
    )
    assert provider.calls == []  # provider never called for empty input


def test_refresh_upserts_returned_events(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyEarningsEventRepository(connection, _readiness())
    provider = _StubProvider(
        [
            EodhdEarningsEvent(
                symbol="AAPL.US",
                event_date=date(2026, 7, 30),
                status="confirmed",
                raw_payload={"eps_estimate": "1.45"},
            ),
            EodhdEarningsEvent(
                symbol="MSFT.US",
                event_date=date(2026, 7, 22),
                status="estimated",
                raw_payload={},
            ),
        ]
    )
    summary = refresh_earnings_calendar(
        provider=provider,
        repository=repo,
        symbols=["AAPL.US", "MSFT.US"],
        today=_TODAY,
        window_days=21,
        source="eodhd",
        fetched_at=_NOW,
    )
    assert summary.fetched_count == 2
    assert summary.upserted_count == 2
    assert summary.error_text is None
    persisted = repo.list_upcoming(
        from_date=_TODAY, to_date=date(2026, 12, 31)
    ).records
    symbols = [r.symbol for r in persisted]
    assert symbols == ["MSFT.US", "AAPL.US"]


def test_refresh_overwrites_existing_event(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyEarningsEventRepository(connection, _readiness())
    # First refresh — date is estimated.
    refresh_earnings_calendar(
        provider=_StubProvider(
            [
                EodhdEarningsEvent(
                    symbol="AAPL.US",
                    event_date=date(2026, 7, 30),
                    status="estimated",
                    raw_payload={},
                )
            ]
        ),
        repository=repo,
        symbols=["AAPL.US"],
        today=_TODAY,
        window_days=21,
        source="eodhd",
        fetched_at=_NOW,
    )
    # Second refresh — provider promotes it to confirmed.
    refresh_earnings_calendar(
        provider=_StubProvider(
            [
                EodhdEarningsEvent(
                    symbol="AAPL.US",
                    event_date=date(2026, 7, 30),
                    status="confirmed",
                    raw_payload={"eps_estimate": "1.50"},
                )
            ]
        ),
        repository=repo,
        symbols=["AAPL.US"],
        today=_TODAY,
        window_days=21,
        source="eodhd",
        fetched_at=_NOW,
    )
    persisted = repo.list_upcoming(
        from_date=_TODAY, to_date=date(2026, 12, 31)
    ).records
    assert len(persisted) == 1
    assert persisted[0].status == "confirmed"


def test_refresh_swallows_provider_failure(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyEarningsEventRepository(connection, _readiness())
    summary = refresh_earnings_calendar(
        provider=_FailingProvider(),
        repository=repo,
        symbols=["AAPL.US"],
        today=_TODAY,
        window_days=21,
        source="eodhd",
        fetched_at=_NOW,
    )
    assert summary.fetched_count == 0
    assert summary.upserted_count == 0
    assert summary.symbols_requested == 1
    assert summary.error_text is not None
    assert "eodhd_quota_exhausted" in summary.error_text


def test_refresh_uses_window_days_for_provider_to_date(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyEarningsEventRepository(connection, _readiness())
    provider = _StubProvider([])
    refresh_earnings_calendar(
        provider=provider,
        repository=repo,
        symbols=["AAPL.US"],
        today=date(2026, 6, 12),
        window_days=14,
        source="eodhd",
        fetched_at=_NOW,
    )
    symbols, from_date, to_date = provider.calls[0]
    assert symbols == ("AAPL.US",)
    assert from_date == date(2026, 6, 12)
    assert to_date == date(2026, 6, 26)
