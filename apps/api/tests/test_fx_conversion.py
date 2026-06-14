"""Tests for the FxConverter helper + tax_report EUR-conversie (V1.2 §BB)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from ai_trading_agent_storage import (
    FxRateRecord,
    SqlAlchemyFxRateRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from sqlalchemy import create_engine, text

from portfolio_outlook_api.fx_conversion import FxConverter
from portfolio_outlook_api.tax_report import (
    ExecutionRow,
    build_tax_year_report,
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
                "('0079_macro_index_snapshots')"
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
        latest_expected_revision_id="0079_macro_index_snapshots",
        database_revision_id="0079_macro_index_snapshots",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="ok",
    )


def _seed_eur_pair(
    conn, *, quote_currency: str, rate: str, as_of: date
) -> None:
    repo = SqlAlchemyFxRateRepository(conn, _readiness())
    repo.upsert(
        FxRateRecord(
            base_currency="EUR",
            quote_currency=quote_currency,
            as_of_date=as_of,
            rate=Decimal(rate),
            ingested_ts=datetime(2026, 6, 14, tzinfo=UTC),
            provider="eodhd",
        )
    )


def _ex(
    *,
    exec_id: str,
    side: str,
    price: str,
    qty: str,
    when: datetime,
    symbol: str = "AAPL",
    currency: str = "USD",
) -> ExecutionRow:
    return ExecutionRow(
        ibkr_exec_id=exec_id,
        account_id="DU1",
        symbol=symbol,
        side=side,
        fill_price_local=Decimal(price),
        fill_quantity=Decimal(qty),
        fill_time=when,
        commission=Decimal("1"),
        commission_currency=currency,
        action_draft_id=None,
    )


def test_converter_returns_one_for_eur(connection) -> None:  # type: ignore[no-untyped-def]
    converter = FxConverter(SqlAlchemyFxRateRepository(connection, _readiness()))
    eur, lookup = converter.to_eur(
        amount=Decimal("100"), currency="EUR", on_date=date(2026, 5, 12)
    )
    assert eur == Decimal("100")
    assert lookup is not None
    assert lookup.rate_to_eur == Decimal("1")


def test_converter_uses_eur_base_pair(connection) -> None:  # type: ignore[no-untyped-def]
    """EUR/USD = 1.10 → 100 USD = 100 / 1.10 EUR ≈ 90.91."""

    _seed_eur_pair(
        connection, quote_currency="USD", rate="1.10", as_of=date(2026, 5, 12)
    )
    converter = FxConverter(SqlAlchemyFxRateRepository(connection, _readiness()))
    eur, lookup = converter.to_eur(
        amount=Decimal("100"), currency="USD", on_date=date(2026, 5, 12)
    )
    assert eur is not None
    assert lookup is not None
    assert round(float(eur), 2) == round(100 / 1.10, 2)


def test_converter_falls_back_to_nearest_prior_date(connection) -> None:  # type: ignore[no-untyped-def]
    """Friday rate gebruikt voor zaterdag-transactie."""

    _seed_eur_pair(
        connection, quote_currency="USD", rate="1.10", as_of=date(2026, 5, 8)
    )
    converter = FxConverter(SqlAlchemyFxRateRepository(connection, _readiness()))
    # Zaterdag — geen rate; gebruikt vrijdag.
    eur, lookup = converter.to_eur(
        amount=Decimal("100"), currency="USD", on_date=date(2026, 5, 9)
    )
    assert eur is not None
    assert lookup is not None
    assert lookup.rate_date == date(2026, 5, 8)


def test_converter_returns_none_when_no_rate(connection) -> None:  # type: ignore[no-untyped-def]
    converter = FxConverter(SqlAlchemyFxRateRepository(connection, _readiness()))
    eur, lookup = converter.to_eur(
        amount=Decimal("100"), currency="JPY", on_date=date(2026, 5, 12)
    )
    assert eur is None
    assert lookup is None


def test_converter_caches_per_currency_date(connection) -> None:  # type: ignore[no-untyped-def]
    _seed_eur_pair(
        connection, quote_currency="USD", rate="1.10", as_of=date(2026, 5, 12)
    )
    converter = FxConverter(SqlAlchemyFxRateRepository(connection, _readiness()))
    converter.to_eur(amount=Decimal("100"), currency="USD", on_date=date(2026, 5, 12))
    # Tweede call hetzelfde key — cache hit (geen DB roundtrip nodig
    # voor correctness, maar wel voor performance).
    eur2, _ = converter.to_eur(
        amount=Decimal("200"), currency="USD", on_date=date(2026, 5, 12)
    )
    assert eur2 == Decimal("200") / Decimal("1.10")


def test_build_report_fills_eur_when_converter_present(connection) -> None:  # type: ignore[no-untyped-def]
    """End-to-end: tax-report bevat EUR-velden + jaartotal."""

    _seed_eur_pair(
        connection, quote_currency="USD", rate="1.10", as_of=date(2026, 1, 1)
    )
    _seed_eur_pair(
        connection, quote_currency="USD", rate="1.10", as_of=date(2026, 5, 12)
    )
    converter = FxConverter(SqlAlchemyFxRateRepository(connection, _readiness()))

    executions = (
        _ex(
            exec_id="b1", side="BUY", price="100", qty="10",
            when=datetime(2026, 1, 10, tzinfo=UTC),
        ),
        _ex(
            exec_id="s1", side="SELL", price="120", qty="10",
            when=datetime(2026, 5, 12, tzinfo=UTC),
        ),
    )
    report = build_tax_year_report(
        year=2026, executions=executions, fx_converter=converter
    )
    assert len(report.realised_trades) == 1
    trade = report.realised_trades[0]
    assert trade.net_eur is not None
    assert trade.gross_eur is not None
    # Jaartotal in EUR.
    assert report.year_totals.net_eur_total is not None
    assert report.year_totals.eur_conversion_coverage_pct == 100.0
    assert report.fx_conversion_available is True


def test_build_report_falls_back_to_local_only_when_no_fx(connection) -> None:  # type: ignore[no-untyped-def]
    """Geen FX-data → coverage 0 %, notes mentioneren dat."""

    converter = FxConverter(SqlAlchemyFxRateRepository(connection, _readiness()))
    executions = (
        _ex(
            exec_id="b1", side="BUY", price="100", qty="10",
            when=datetime(2026, 1, 10, tzinfo=UTC),
        ),
        _ex(
            exec_id="s1", side="SELL", price="120", qty="10",
            when=datetime(2026, 5, 12, tzinfo=UTC),
        ),
    )
    report = build_tax_year_report(
        year=2026, executions=executions, fx_converter=converter
    )
    assert report.realised_trades[0].net_eur is None
    assert report.year_totals.net_eur_total is None
    assert report.year_totals.eur_conversion_coverage_pct == 0.0
    assert any("EUR-conversie" in note for note in report.notes_nl)
