"""Tests voor ``SqlAlchemyMacroIndexSnapshotRepository`` (V1.2 §BE)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text

from ai_trading_agent_storage import (
    MACRO_SERIES_SPX,
    MACRO_SERIES_VIX,
    MacroIndexSnapshotRecord,
    SaveMacroIndexSnapshotRequest,
    SqlAlchemyMacroIndexSnapshotRepository,
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
                "VALUES ('0079_macro_index_snapshots')"
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


def _req(
    *,
    snapshot_id: str = "snap-1",
    series: str = MACRO_SERIES_VIX,
    bar_date: date = date(2026, 6, 13),
    close: str = "15.5",
) -> SaveMacroIndexSnapshotRequest:
    return SaveMacroIndexSnapshotRequest(
        snapshot_id=snapshot_id,
        series_code=series,
        bar_date=bar_date,
        close_value=Decimal(close),
        raw_payload={"open": "15.3"},
        provider="eodhd",
        fetched_at=datetime(2026, 6, 14, tzinfo=UTC),
    )


def test_record_rejects_non_positive_close() -> None:
    with pytest.raises(ValueError, match="close_value"):
        MacroIndexSnapshotRecord(
            snapshot_id="s",
            series_code=MACRO_SERIES_VIX,
            bar_date=date(2026, 6, 1),
            close_value=Decimal(0),
            raw_payload=None,
            provider="eodhd",
            fetched_at=datetime(2026, 6, 14, tzinfo=UTC),
        )


def test_record_rejects_empty_series() -> None:
    with pytest.raises(ValueError, match="series_code"):
        MacroIndexSnapshotRecord(
            snapshot_id="s",
            series_code="",
            bar_date=date(2026, 6, 1),
            close_value=Decimal(10),
            raw_payload=None,
            provider="eodhd",
            fetched_at=datetime(2026, 6, 14, tzinfo=UTC),
        )


def test_upsert_inserts_new_row(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyMacroIndexSnapshotRepository(connection, _readiness())
    res = repo.upsert(_req())
    assert res.accepted is True
    listed = repo.list_bars(series_code=MACRO_SERIES_VIX)
    assert len(listed.records) == 1
    assert listed.records[0].close_value == Decimal("15.5")


def test_upsert_is_idempotent_per_series_date(connection) -> None:  # type: ignore[no-untyped-def]
    """Refetch upsert in plaats van duplicate."""

    repo = SqlAlchemyMacroIndexSnapshotRepository(connection, _readiness())
    repo.upsert(_req(snapshot_id="s-old", close="15.0"))
    repo.upsert(_req(snapshot_id="s-new", close="16.0"))
    listed = repo.list_bars(series_code=MACRO_SERIES_VIX)
    assert len(listed.records) == 1
    assert listed.records[0].snapshot_id == "s-new"
    assert listed.records[0].close_value == Decimal("16.0")


def test_get_latest_value_returns_most_recent(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyMacroIndexSnapshotRepository(connection, _readiness())
    repo.upsert(_req(snapshot_id="s1", bar_date=date(2026, 6, 10), close="15.0"))
    repo.upsert(_req(snapshot_id="s2", bar_date=date(2026, 6, 13), close="22.5"))
    latest = repo.get_latest_value(series_code=MACRO_SERIES_VIX)
    assert latest is not None
    assert latest.close_value == Decimal("22.5")
    assert latest.bar_date == date(2026, 6, 13)


def test_get_latest_value_respects_on_or_before(connection) -> None:  # type: ignore[no-untyped-def]
    """Voor een audit-datum willen we de bar van toen, niet de huidige."""

    repo = SqlAlchemyMacroIndexSnapshotRepository(connection, _readiness())
    repo.upsert(_req(snapshot_id="s1", bar_date=date(2026, 6, 10), close="15.0"))
    repo.upsert(_req(snapshot_id="s2", bar_date=date(2026, 6, 13), close="22.5"))
    historical = repo.get_latest_value(
        series_code=MACRO_SERIES_VIX, on_or_before=date(2026, 6, 11)
    )
    assert historical is not None
    assert historical.close_value == Decimal("15.0")


def test_get_latest_value_returns_none_for_empty_series(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyMacroIndexSnapshotRepository(connection, _readiness())
    assert repo.get_latest_value(series_code=MACRO_SERIES_VIX) is None


def test_list_bars_chronological(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyMacroIndexSnapshotRepository(connection, _readiness())
    repo.upsert(_req(snapshot_id="s2", bar_date=date(2026, 6, 13), close="22.5"))
    repo.upsert(_req(snapshot_id="s1", bar_date=date(2026, 6, 10), close="15.0"))
    listed = repo.list_bars(series_code=MACRO_SERIES_VIX)
    assert [r.bar_date for r in listed.records] == [
        date(2026, 6, 10),
        date(2026, 6, 13),
    ]


def test_list_bars_filters_date_range(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyMacroIndexSnapshotRepository(connection, _readiness())
    for i, day in enumerate([5, 7, 10, 13]):
        repo.upsert(
            _req(
                snapshot_id=f"s{i}",
                bar_date=date(2026, 6, day),
                close="15",
            )
        )
    listed = repo.list_bars(
        series_code=MACRO_SERIES_VIX,
        from_date=date(2026, 6, 7),
        to_date=date(2026, 6, 11),
    )
    assert [r.bar_date for r in listed.records] == [
        date(2026, 6, 7),
        date(2026, 6, 10),
    ]


def test_list_bars_scopes_per_series(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyMacroIndexSnapshotRepository(connection, _readiness())
    repo.upsert(_req(snapshot_id="vix1", series=MACRO_SERIES_VIX, close="15"))
    repo.upsert(_req(snapshot_id="spx1", series=MACRO_SERIES_SPX, close="5000"))
    vix = repo.list_bars(series_code=MACRO_SERIES_VIX)
    spx = repo.list_bars(series_code=MACRO_SERIES_SPX)
    assert len(vix.records) == 1
    assert len(spx.records) == 1
    assert vix.records[0].close_value == Decimal("15")
    assert spx.records[0].close_value == Decimal("5000")


def test_list_bars_rejects_zero_limit(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyMacroIndexSnapshotRepository(connection, _readiness())
    with pytest.raises(ValueError, match="limit"):
        repo.list_bars(series_code=MACRO_SERIES_VIX, limit=0)
