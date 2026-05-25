"""Task 128 — cold-start storage repository tests.

Covers the three new repositories + the seed-write half of the
watchlist-items table. Idempotency is enforced via the
``UNIQUE``-on-``ibkr_account_id`` primary key on
``cold_start_seed_audit``; the repository raises
``ColdStartAlreadySeededError`` on a second call.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    ColdStartAlreadySeededError,
    ColdStartSeedAuditEntry,
    SqlAlchemyColdStartSeedAuditRepository,
    SqlAlchemyWatchlistConfirmationAuditRepository,
    SqlAlchemyWatchlistConfirmationStateRepository,
    SqlAlchemyWatchlistItemSeedRepository,
    WatchlistConfirmationAuditEntry,
    WatchlistConfirmationStateRecord,
    WatchlistItemSeedRecord,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)


def _report(allowed: bool) -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=(
            MigrationReadinessStatus.MIGRATIONS_CURRENT
            if allowed
            else MigrationReadinessStatus.NOT_CONNECTED
        ),
        database_connected=allowed,
        migrations_checked_against_database=allowed,
        offline_inventory_valid=True,
        latest_expected_revision_id="0047_cold_start_and_watchlist_confirmation",
        database_revision_id=(
            "0047_cold_start_and_watchlist_confirmation"
            if allowed
            else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


_BASE = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


def _watchlist_item(
    *,
    watchlist_item_id: str = "wi-1",
    ibkr_account_id: str = "DU1234567",
    symbol: str = "SXR8",
    source: str = "cold_start_seed",
    is_starter_seed: bool = True,
) -> WatchlistItemSeedRecord:
    return WatchlistItemSeedRecord(
        watchlist_item_id=watchlist_item_id,
        ibkr_account_id=ibkr_account_id,
        asset_id=None,
        symbol=symbol,
        name=f"{symbol} starter",
        exchange="XETRA",
        currency="EUR",
        security_type="ETF",
        status="active",
        source=source,
        is_starter_seed=is_starter_seed,
        seed_version="v1",
        created_at=_BASE,
        updated_at=_BASE,
    )


# ---- cold_start_seed_audit ---------------------------------------


def test_seed_audit_append_then_find_by_account() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyColdStartSeedAuditRepository(conn, _report(True))

        repo.append(
            ColdStartSeedAuditEntry(
                seeded_at=_BASE,
                ibkr_account_id="DU1234567",
                seeded_count=12,
                failed_conids_json="[]",
                seed_version="v1",
            )
        )
        found = repo.find_by_account_id("DU1234567")
        assert found is not None
        assert found.seeded_count == 12
        assert repo.find_by_account_id("DU9999999") is None


def test_seed_audit_rejects_second_append_for_same_account() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyColdStartSeedAuditRepository(conn, _report(True))
        record = ColdStartSeedAuditEntry(
            seeded_at=_BASE,
            ibkr_account_id="DU1234567",
            seeded_count=12,
            failed_conids_json="[]",
            seed_version="v1",
        )
        repo.append(record)
        with pytest.raises(ColdStartAlreadySeededError):
            repo.append(record)


def test_seed_audit_rejects_negative_count() -> None:
    with pytest.raises(ValueError, match="seeded_count"):
        ColdStartSeedAuditEntry(
            seeded_at=_BASE,
            ibkr_account_id="DU1234567",
            seeded_count=-1,
            failed_conids_json="[]",
            seed_version="v1",
        )


def test_seed_audit_rejects_empty_account_id() -> None:
    with pytest.raises(ValueError, match="ibkr_account_id"):
        ColdStartSeedAuditEntry(
            seeded_at=_BASE,
            ibkr_account_id="",
            seeded_count=12,
            failed_conids_json="[]",
            seed_version="v1",
        )


# ---- watchlist_confirmation_state -------------------------------


def test_confirmation_state_upsert_inserts_then_updates() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyWatchlistConfirmationStateRepository(
            conn, _report(True)
        )

        repo.upsert(
            WatchlistConfirmationStateRecord(
                ibkr_account_id="DU1234567",
                state="unconfirmed",
                last_updated_at=_BASE,
            )
        )
        assert repo.get_by_account_id("DU1234567").state == "unconfirmed"
        assert len(repo.list_all().records) == 1

        repo.upsert(
            WatchlistConfirmationStateRecord(
                ibkr_account_id="DU1234567",
                state="confirmed",
                last_updated_at=_BASE + timedelta(minutes=5),
            )
        )
        rows = repo.list_all()
        assert len(rows.records) == 1
        assert rows.records[0].state == "confirmed"


def test_confirmation_state_rejects_unknown_state() -> None:
    with pytest.raises(ValueError, match="state"):
        WatchlistConfirmationStateRecord(
            ibkr_account_id="DU1234567",
            state="freaky",
            last_updated_at=_BASE,
        )


# ---- watchlist_confirmation_audit -------------------------------


def test_confirmation_audit_append_and_list_by_account() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyWatchlistConfirmationAuditRepository(
            conn, _report(True)
        )

        repo.append(
            WatchlistConfirmationAuditEntry(
                event_at=_BASE,
                ibkr_account_id="DU1234567",
                from_state="absent",
                to_state="unconfirmed",
                actor="system",
                row_count_at_event=12,
                details_json=None,
            )
        )
        repo.append(
            WatchlistConfirmationAuditEntry(
                event_at=_BASE + timedelta(minutes=5),
                ibkr_account_id="DU1234567",
                from_state="unconfirmed",
                to_state="confirmed",
                actor="user",
                row_count_at_event=11,
                details_json=None,
            )
        )
        rows = repo.list_by_account_id(ibkr_account_id="DU1234567")
        assert len(rows.records) == 2
        # Newest first.
        assert rows.records[0].actor == "user"
        assert rows.records[1].actor == "system"


def test_confirmation_audit_rejects_unknown_actor() -> None:
    with pytest.raises(ValueError, match="actor"):
        WatchlistConfirmationAuditEntry(
            event_at=_BASE,
            ibkr_account_id="DU1234567",
            from_state="absent",
            to_state="unconfirmed",
            actor="root",
            row_count_at_event=0,
            details_json=None,
        )


def test_confirmation_audit_rejects_unknown_to_state() -> None:
    with pytest.raises(ValueError, match="to_state"):
        WatchlistConfirmationAuditEntry(
            event_at=_BASE,
            ibkr_account_id="DU1234567",
            from_state="absent",
            to_state="absent",  # not in to-state set
            actor="system",
            row_count_at_event=0,
            details_json=None,
        )


def test_confirmation_audit_no_update_or_delete_methods() -> None:
    forbidden = {"update", "delete", "upsert", "save_or_update"}
    public_methods = {
        name
        for name in dir(SqlAlchemyWatchlistConfirmationAuditRepository)
        if not name.startswith("_")
    }
    assert forbidden.isdisjoint(public_methods)


# ---- watchlist_items seed path -----------------------------------


def test_watchlist_item_seed_append_and_count_active() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyWatchlistItemSeedRepository(conn, _report(True))

        for i in range(5):
            repo.append(_watchlist_item(watchlist_item_id=f"wi-{i}", symbol=f"S{i}"))

        assert repo.count_active_for_account("DU1234567") == 5
        assert repo.count_active_for_account("DU9999999") == 0


def test_watchlist_item_seed_archive_by_id_flips_status() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyWatchlistItemSeedRepository(conn, _report(True))
        repo.append(_watchlist_item(watchlist_item_id="wi-1"))
        assert repo.count_active_for_account("DU1234567") == 1

        archived = repo.archive_by_id(
            watchlist_item_id="wi-1", ibkr_account_id="DU1234567"
        )
        assert archived is True
        assert repo.count_active_for_account("DU1234567") == 0


def test_watchlist_item_seed_list_starter_seed_for_account() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyWatchlistItemSeedRepository(conn, _report(True))
        repo.append(_watchlist_item(watchlist_item_id="wi-A", symbol="SXR8"))
        repo.append(_watchlist_item(watchlist_item_id="wi-B", symbol="VWCE"))
        rows = repo.list_starter_seed_for_account("DU1234567")
        assert len(rows.records) == 2
        # Sorted ascending by symbol.
        assert rows.records[0].symbol == "SXR8"
        assert rows.records[1].symbol == "VWCE"


def test_watchlist_item_seed_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="source"):
        WatchlistItemSeedRecord(
            watchlist_item_id="wi-1",
            ibkr_account_id="DU1234567",
            asset_id=None,
            symbol="SXR8",
            name=None,
            exchange=None,
            currency=None,
            security_type=None,
            status="active",
            source="freaky",
            is_starter_seed=True,
            seed_version="v1",
            created_at=_BASE,
            updated_at=_BASE,
        )


def test_watchlist_item_seed_archived_row_not_counted_active() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyWatchlistItemSeedRepository(conn, _report(True))
        repo.append(
            WatchlistItemSeedRecord(
                watchlist_item_id="wi-archived",
                ibkr_account_id="DU1234567",
                asset_id=None,
                symbol="SXR8",
                name=None,
                exchange=None,
                currency=None,
                security_type=None,
                status="archived",
                source="cold_start_seed",
                is_starter_seed=True,
                seed_version="v1",
                created_at=_BASE,
                updated_at=_BASE,
            )
        )
        assert repo.count_active_for_account("DU1234567") == 0
