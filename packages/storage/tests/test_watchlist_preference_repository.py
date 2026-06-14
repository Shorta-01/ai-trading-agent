"""Tests for ``SqlAlchemyWatchlistPreferenceRepository`` (V1.2 §AU)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text

from ai_trading_agent_storage import (
    SaveWatchlistPreferenceRequest,
    SqlAlchemyWatchlistPreferenceRepository,
    WatchlistPreferenceRecord,
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


def _readiness(persistence_allowed: bool = True) -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0078_sell_signal_cards",
        database_revision_id="0078_sell_signal_cards",
        persistence_allowed=persistence_allowed,
        blocks_runtime_writes=False,
        explanation_nl="Test readiness — migration up-to-date.",
    )


def _request(
    *,
    pref_id: str = "pref-1",
    account_ref: str = "default",
    symbol: str = "AAPL",
    kind: str = "favorite",
    note: str | None = None,
) -> SaveWatchlistPreferenceRequest:
    return SaveWatchlistPreferenceRequest(
        watchlist_preference_id=pref_id,
        ibkr_account_ref=account_ref,
        symbol=symbol,
        kind=kind,
        note=note,
        created_at=datetime(2026, 6, 13, 8, 0, tzinfo=UTC),
    )


def test_record_rejects_invalid_kind() -> None:
    with pytest.raises(ValueError, match="kind must be"):
        WatchlistPreferenceRecord(
            watchlist_preference_id="pref-1",
            ibkr_account_ref="default",
            symbol="AAPL",
            kind="bogus",
            note=None,
            created_at=datetime(2026, 6, 13, tzinfo=UTC),
        )


def test_request_rejects_invalid_kind() -> None:
    with pytest.raises(ValueError, match="kind must be"):
        SaveWatchlistPreferenceRequest(
            watchlist_preference_id="pref-1",
            ibkr_account_ref="default",
            symbol="AAPL",
            kind="watch",
            note=None,
            created_at=datetime(2026, 6, 13, tzinfo=UTC),
        )


def test_record_rejects_empty_symbol() -> None:
    with pytest.raises(ValueError, match="symbol"):
        WatchlistPreferenceRecord(
            watchlist_preference_id="pref-1",
            ibkr_account_ref="default",
            symbol="",
            kind="favorite",
            note=None,
            created_at=datetime(2026, 6, 13, tzinfo=UTC),
        )


def test_upsert_inserts_new_row(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyWatchlistPreferenceRepository(connection, _readiness())
    result = repo.upsert_preference(_request())
    assert result.accepted is True
    assert result.record_id == "pref-1"
    listed = repo.list_for_account(ibkr_account_ref="default")
    assert len(listed.records) == 1
    assert listed.records[0].symbol == "AAPL"
    assert listed.records[0].kind == "favorite"


def test_upsert_is_idempotent_on_account_symbol_kind(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyWatchlistPreferenceRepository(connection, _readiness())
    repo.upsert_preference(_request(pref_id="pref-old", note="oude tekst"))
    repo.upsert_preference(_request(pref_id="pref-new", note="nieuwe tekst"))
    listed = repo.list_for_account(ibkr_account_ref="default", kind="favorite")
    assert len(listed.records) == 1
    assert listed.records[0].watchlist_preference_id == "pref-new"
    assert listed.records[0].note == "nieuwe tekst"


def test_favorite_and_excluded_coexist_for_same_symbol(connection) -> None:  # type: ignore[no-untyped-def]
    """The UNIQUE key is per-kind, so the same operator could in
    principle add ``AAPL`` to both lists (UI prevents this but the
    storage must not error)."""

    repo = SqlAlchemyWatchlistPreferenceRepository(connection, _readiness())
    repo.upsert_preference(_request(pref_id="pref-fav", kind="favorite"))
    repo.upsert_preference(_request(pref_id="pref-exc", kind="excluded"))
    all_prefs = repo.list_for_account(ibkr_account_ref="default")
    assert {r.kind for r in all_prefs.records} == {"favorite", "excluded"}


def test_list_for_account_filters_by_kind(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyWatchlistPreferenceRepository(connection, _readiness())
    repo.upsert_preference(_request(pref_id="p1", symbol="AAPL", kind="favorite"))
    repo.upsert_preference(
        _request(pref_id="p2", symbol="ASML.AS", kind="favorite")
    )
    repo.upsert_preference(_request(pref_id="p3", symbol="TSLA", kind="excluded"))
    favs = repo.list_for_account(ibkr_account_ref="default", kind="favorite")
    excs = repo.list_for_account(ibkr_account_ref="default", kind="excluded")
    assert [r.symbol for r in favs.records] == ["AAPL", "ASML.AS"]
    assert [r.symbol for r in excs.records] == ["TSLA"]


def test_list_for_account_is_account_scoped(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyWatchlistPreferenceRepository(connection, _readiness())
    repo.upsert_preference(_request(pref_id="p1", account_ref="account-a"))
    repo.upsert_preference(_request(pref_id="p2", account_ref="account-b"))
    listed = repo.list_for_account(ibkr_account_ref="account-a")
    assert [r.watchlist_preference_id for r in listed.records] == ["p1"]


def test_delete_preference_removes_row(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyWatchlistPreferenceRepository(connection, _readiness())
    repo.upsert_preference(_request())
    result = repo.delete_preference(
        ibkr_account_ref="default", symbol="AAPL", kind="favorite"
    )
    assert result.accepted is True
    assert repo.list_for_account(ibkr_account_ref="default").records == ()


def test_delete_preference_is_idempotent(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyWatchlistPreferenceRepository(connection, _readiness())
    result = repo.delete_preference(
        ibkr_account_ref="default", symbol="NOPE", kind="favorite"
    )
    assert result.accepted is True


def test_list_excluded_symbols_returns_frozenset(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyWatchlistPreferenceRepository(connection, _readiness())
    repo.upsert_preference(_request(pref_id="p1", symbol="TSLA", kind="excluded"))
    repo.upsert_preference(_request(pref_id="p2", symbol="GME", kind="excluded"))
    repo.upsert_preference(_request(pref_id="p3", symbol="AAPL", kind="favorite"))
    excluded = repo.list_excluded_symbols(ibkr_account_ref="default")
    assert isinstance(excluded, frozenset)
    assert excluded == frozenset({"TSLA", "GME"})


def test_list_excluded_symbols_is_account_scoped(connection) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyWatchlistPreferenceRepository(connection, _readiness())
    repo.upsert_preference(
        _request(pref_id="p1", account_ref="account-a", symbol="TSLA", kind="excluded")
    )
    repo.upsert_preference(
        _request(pref_id="p2", account_ref="account-b", symbol="GME", kind="excluded")
    )
    assert repo.list_excluded_symbols(ibkr_account_ref="account-a") == frozenset(
        {"TSLA"}
    )
    assert repo.list_excluded_symbols(ibkr_account_ref="account-b") == frozenset(
        {"GME"}
    )
