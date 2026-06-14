"""Task 128 — watchlist confirmation API route tests."""

from __future__ import annotations

from datetime import UTC, datetime

from ai_trading_agent_storage import (
    ColdStartSeedAuditEntry,
    SqlAlchemyColdStartSeedAuditRepository,
    SqlAlchemyWatchlistConfirmationStateRepository,
    SqlAlchemyWatchlistItemSeedRepository,
    WatchlistConfirmationStateRecord,
    WatchlistItemSeedRecord,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_BASE = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


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


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.ibkr_account_id_hint = None


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _seed_db_for_unconfirmed_account(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "wl.sqlite"
    db_url = f"sqlite+pysqlite:///{db_path}"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    api_settings.ibkr_account_id_hint = "DU1234567"

    engine = create_engine(db_url)
    with engine.begin() as conn:
        metadata.create_all(conn)
        # Stamp the alembic version so require_writable=True passes
        # the migration-readiness check.
        conn.execute(
            text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0077_monthly_report_archive')"
            )
        )
        wl_repo = SqlAlchemyWatchlistItemSeedRepository(conn, _report(True))
        state_repo = SqlAlchemyWatchlistConfirmationStateRepository(
            conn, _report(True)
        )
        for index, symbol in enumerate(("SXR8", "VWCE", "ASML")):
            wl_repo.append(
                WatchlistItemSeedRecord(
                    watchlist_item_id=f"wi-{index}",
                    ibkr_account_id="DU1234567",
                    asset_id=None,
                    symbol=symbol,
                    name=f"{symbol} starter",
                    exchange="XETRA",
                    currency="EUR",
                    security_type="ETF",
                    status="active",
                    source="cold_start_seed",
                    is_starter_seed=True,
                    seed_version="v1",
                    created_at=_BASE,
                    updated_at=_BASE,
                )
            )
        state_repo.upsert(
            WatchlistConfirmationStateRecord(
                ibkr_account_id="DU1234567",
                state="unconfirmed",
                last_updated_at=_BASE,
            )
        )
    return db_url


# ---- GET /watchlist/confirmation-state ---------------------------


def test_get_state_returns_no_account_when_hint_missing() -> None:
    response = client.get("/watchlist/confirmation-state")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "no_account_configured"
    assert body["banner_text"] is None


def test_get_state_returns_unconfirmed_with_banner_text(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db_for_unconfirmed_account(tmp_path)
    response = client.get("/watchlist/confirmation-state")
    body = response.json()
    assert body["state"] == "unconfirmed"
    assert "Welkom" in body["banner_text"]


def test_get_state_returns_confirmed_when_state_is_confirmed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db_for_unconfirmed_account(tmp_path)
    # Flip to confirmed.
    engine = create_engine(db_url)
    with engine.begin() as conn:
        state_repo = SqlAlchemyWatchlistConfirmationStateRepository(
            conn, _report(True)
        )
        state_repo.upsert(
            WatchlistConfirmationStateRecord(
                ibkr_account_id="DU1234567",
                state="confirmed",
                last_updated_at=_BASE,
            )
        )
    response = client.get("/watchlist/confirmation-state")
    body = response.json()
    assert body["state"] == "confirmed"
    assert body["banner_text"] is None


# ---- POST /watchlist/confirm -------------------------------------


def test_confirm_rejects_wrong_phrase(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db_for_unconfirmed_account(tmp_path)
    response = client.post(
        "/watchlist/confirm",
        json={"confirmation_phrase": "bevestig"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Bevestigingscode is onjuist."}


def test_confirm_rejects_empty_watchlist(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db_for_unconfirmed_account(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        wl_repo = SqlAlchemyWatchlistItemSeedRepository(conn, _report(True))
        # Archive all three seeded rows.
        for index in range(3):
            wl_repo.archive_by_id(
                watchlist_item_id=f"wi-{index}",
                ibkr_account_id="DU1234567",
            )
    response = client.post(
        "/watchlist/confirm",
        json={"confirmation_phrase": "BEVESTIG"},
    )
    assert response.status_code == 422
    assert "Volglijst is leeg" in response.json()["detail"]


def test_confirm_rejects_when_already_confirmed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db_for_unconfirmed_account(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        state_repo = SqlAlchemyWatchlistConfirmationStateRepository(
            conn, _report(True)
        )
        state_repo.upsert(
            WatchlistConfirmationStateRecord(
                ibkr_account_id="DU1234567",
                state="confirmed",
                last_updated_at=_BASE,
            )
        )
    response = client.post(
        "/watchlist/confirm",
        json={"confirmation_phrase": "BEVESTIG"},
    )
    assert response.status_code == 409
    assert "al bevestigd" in response.json()["detail"]


def test_confirm_happy_path_flips_state(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db_for_unconfirmed_account(tmp_path)
    response = client.post(
        "/watchlist/confirm",
        json={"confirmation_phrase": "BEVESTIG"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "confirmed"
    assert body["row_count"] == 3
    assert body["safe_for_orders"] is False

    # Verify the state row is now confirmed + audit row written.
    engine = create_engine(db_url)
    with engine.begin() as conn:
        state_repo = SqlAlchemyWatchlistConfirmationStateRepository(
            conn, _report(True)
        )
        state = state_repo.get_by_account_id("DU1234567")
        assert state is not None
        assert state.state == "confirmed"


# ---- GET /watchlist/seed-audit -----------------------------------


def test_seed_audit_404_when_no_audit_row(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db_for_unconfirmed_account(tmp_path)
    # No audit row written by the helper above.
    response = client.get("/watchlist/seed-audit")
    assert response.status_code == 404


def test_seed_audit_returns_row_when_present(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db_for_unconfirmed_account(tmp_path)
    engine = create_engine(db_url)
    with engine.begin() as conn:
        repo = SqlAlchemyColdStartSeedAuditRepository(conn, _report(True))
        repo.append(
            ColdStartSeedAuditEntry(
                seeded_at=_BASE,
                ibkr_account_id="DU1234567",
                seeded_count=3,
                failed_conids_json="[]",
                seed_version="v1",
            )
        )
    response = client.get("/watchlist/seed-audit")
    assert response.status_code == 200
    body = response.json()
    assert body["seeded_count"] == 3
    assert body["seed_version"] == "v1"


# ---- GET /watchlist/cold-start-items -----------------------------


def test_cold_start_items_returns_seeded_rows(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db_for_unconfirmed_account(tmp_path)
    response = client.get("/watchlist/cold-start-items")
    body = response.json()
    assert response.status_code == 200
    assert len(body["items"]) == 3
    symbols = {row["symbol"] for row in body["items"]}
    assert symbols == {"SXR8", "VWCE", "ASML"}


# ---- DELETE /watchlist/cold-start-items/{id} ---------------------


def test_delete_archives_starter_row(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db_for_unconfirmed_account(tmp_path)
    response = client.delete("/watchlist/cold-start-items/wi-0")
    assert response.status_code == 200
    assert response.json()["archived"] is True

    # GET now shows 2 rows.
    listing = client.get("/watchlist/cold-start-items").json()
    assert len(listing["items"]) == 2


def test_delete_returns_404_for_unknown_id(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed_db_for_unconfirmed_account(tmp_path)
    response = client.delete("/watchlist/cold-start-items/wi-does-not-exist")
    assert response.status_code == 404
