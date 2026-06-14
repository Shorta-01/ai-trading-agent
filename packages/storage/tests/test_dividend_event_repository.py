"""Tests for ``SqlAlchemyDividendEventRepository`` (V1.2 §BA)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text

from ai_trading_agent_storage import (
    WITHHOLDING_DEFAULTS_BY_COUNTRY,
    DividendEventRecord,
    SaveDividendEventRequest,
    SqlAlchemyDividendEventRepository,
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
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('0078_sell_signal_cards')"
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
        latest_expected_revision_id="0078_sell_signal_cards",
        database_revision_id="0078_sell_signal_cards",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="ok",
    )


def _request(
    *,
    dividend_id: str = "div-1",
    symbol: str = "AAPL",
    pay_date: date = date(2026, 5, 12),
    currency: str = "USD",
    gross: str = "100",
    withholding_pct: str = "15",
    country_code: str | None = "US",
) -> SaveDividendEventRequest:
    gross_dec = Decimal(gross)
    pct = Decimal(withholding_pct)
    wh = (gross_dec * pct / Decimal(100)).quantize(Decimal("0.01"))
    return SaveDividendEventRequest(
        dividend_event_id=dividend_id,
        ibkr_account_ref="default",
        symbol=symbol,
        isin=None,
        pay_date=pay_date,
        currency_local=currency,
        gross_local=gross_dec,
        withholding_pct=pct,
        withholding_local=wh,
        net_local=gross_dec - wh,
        country_code=country_code,
        note=None,
        created_at=datetime(2026, 6, 13, tzinfo=UTC),
    )


def test_record_rejects_invalid_withholding_pct() -> None:
    with pytest.raises(ValueError, match="withholding_pct"):
        DividendEventRecord(
            dividend_event_id="d",
            ibkr_account_ref="default",
            symbol="AAPL",
            isin=None,
            pay_date=date(2026, 1, 1),
            currency_local="USD",
            gross_local=Decimal(100),
            withholding_pct=Decimal(150),
            withholding_local=Decimal(0),
            net_local=Decimal(100),
            country_code="US",
            note=None,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_record_rejects_negative_gross() -> None:
    with pytest.raises(ValueError, match="gross_local"):
        DividendEventRecord(
            dividend_event_id="d",
            ibkr_account_ref="default",
            symbol="AAPL",
            isin=None,
            pay_date=date(2026, 1, 1),
            currency_local="USD",
            gross_local=Decimal(-1),
            withholding_pct=Decimal(15),
            withholding_local=Decimal(0),
            net_local=Decimal(0),
            country_code="US",
            note=None,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_save_dividend_persists(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyDividendEventRepository(connection, _readiness())
    result = repo.save_dividend(_request())
    assert result.accepted is True
    listed = repo.list_for_account(ibkr_account_ref="default")
    assert len(listed.records) == 1
    assert listed.records[0].symbol == "AAPL"


def test_list_filters_by_year(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyDividendEventRepository(connection, _readiness())
    repo.save_dividend(_request(dividend_id="d-2025", pay_date=date(2025, 5, 12)))
    repo.save_dividend(_request(dividend_id="d-2026", pay_date=date(2026, 5, 12)))
    listed = repo.list_for_account(ibkr_account_ref="default", year=2026)
    assert len(listed.records) == 1
    assert listed.records[0].dividend_event_id == "d-2026"


def test_delete_dividend_removes_row(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyDividendEventRepository(connection, _readiness())
    repo.save_dividend(_request())
    repo.delete_dividend(dividend_event_id="div-1")
    listed = repo.list_for_account(ibkr_account_ref="default")
    assert listed.records == ()


def test_treaty_defaults_exposed() -> None:
    assert WITHHOLDING_DEFAULTS_BY_COUNTRY["US"] == Decimal("15")
    assert WITHHOLDING_DEFAULTS_BY_COUNTRY["NL"] == Decimal("15")
    assert WITHHOLDING_DEFAULTS_BY_COUNTRY["FR"] == Decimal("12.8")
    assert WITHHOLDING_DEFAULTS_BY_COUNTRY["BE"] == Decimal("0")
