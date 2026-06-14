"""Tests for the sector-spread endpoint (V1.2 §AV)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app

_BASE_TS = datetime(2026, 6, 13, 9, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _reset_storage_settings():  # type: ignore[no-untyped-def]
    """Restore shared ``api_settings.storage`` state after each test
    so unrelated tests in the suite are not affected by our tmp_path
    database URLs."""

    original_enabled = api_settings.storage.enabled
    original_url = api_settings.storage.database_url
    original_writes = api_settings.storage.writes_enabled
    yield
    api_settings.storage.enabled = original_enabled
    api_settings.storage.database_url = original_url
    api_settings.storage.writes_enabled = original_writes


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "sector.sqlite")
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
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
    engine.dispose()
    return db_url


def _seed_sync_run(
    db_url: str,
    *,
    sync_run_id: str = "run-1",
    started_at: datetime = _BASE_TS,
) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ibkr_sync_runs ("
                "sync_run_id, started_at, provider_code, "
                "provider_environment, account_mode, status, "
                "account_summary_status, positions_status, "
                "open_orders_status, executions_status, stored_at) "
                "VALUES (:rid, :ts, 'ibkr', 'paper', 'paper', "
                "'success', 'ok', 'ok', 'ok', 'ok', :ts)"
            ),
            {"rid": sync_run_id, "ts": started_at.isoformat()},
        )
    engine.dispose()


def _seed_position(
    db_url: str,
    *,
    snapshot_id: str,
    symbol: str,
    quantity: str,
    average_cost: str,
    sync_run_id: str = "run-1",
) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ibkr_position_snapshots ("
                "snapshot_id, sync_run_id, account_ref, conid, "
                "symbol, security_type, currency, quantity, "
                "average_cost, received_at, stored_at) VALUES ("
                ":sid, :rid, 'default', '1', :sym, 'STK', 'USD', "
                ":qty, :avg, :ts, :ts)"
            ),
            {
                "sid": snapshot_id,
                "rid": sync_run_id,
                "sym": symbol,
                "qty": quantity,
                "avg": average_cost,
                "ts": _BASE_TS.isoformat(),
            },
        )
    engine.dispose()


def _seed_fundamentals(
    db_url: str,
    *,
    snapshot_id: str,
    symbol: str,
    sector: str | None,
    fetched_at: datetime = _BASE_TS,
) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO asset_fundamentals_snapshots ("
                "snapshot_id, eodhd_symbol, symbol, sector, "
                "raw_payload_hash, provider_code, fetched_at, "
                "stored_at) VALUES ("
                ":sid, :sym, :sym, :sec, 'h', 'eodhd', :ts, :ts)"
            ),
            {
                "sid": snapshot_id,
                "sym": symbol,
                "sec": sector,
                "ts": fetched_at.isoformat(),
            },
        )
    engine.dispose()


def _client(db_url: str) -> TestClient:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    return TestClient(app)


def _disable_storage() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def test_empty_when_storage_disabled() -> None:
    _disable_storage()
    body = TestClient(app).get("/portfolio/sector-spread").json()
    assert body["items"] == []
    assert body["total_positions"] == 0


def test_empty_when_no_sync_run(tmp_path) -> None:  # type: ignore[no-untyped-def]
    body = _client(_seed_db(tmp_path)).get("/portfolio/sector-spread").json()
    assert body["items"] == []


def test_groups_positions_by_sector(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_sync_run(db)
    _seed_position(db, snapshot_id="p1", symbol="AAPL", quantity="10", average_cost="100")
    _seed_position(db, snapshot_id="p2", symbol="MSFT", quantity="5", average_cost="200")
    _seed_position(db, snapshot_id="p3", symbol="JNJ", quantity="20", average_cost="50")
    _seed_fundamentals(db, snapshot_id="f1", symbol="AAPL", sector="Technology")
    _seed_fundamentals(db, snapshot_id="f2", symbol="MSFT", sector="Technology")
    _seed_fundamentals(db, snapshot_id="f3", symbol="JNJ", sector="Healthcare")
    body = _client(db).get("/portfolio/sector-spread").json()
    sectors = {item["sector"].lower(): item for item in body["items"]}
    assert "technology" in sectors
    assert "healthcare" in sectors
    # Tech weight: (10*100 + 5*200) / (1000+1000+1000) = 2000/3000 = 66.67
    assert sectors["technology"]["weight_pct"] == 66.67
    assert sectors["healthcare"]["weight_pct"] == 33.33
    assert sectors["technology"]["position_count"] == 2


def test_sorts_items_by_weight_desc(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_sync_run(db)
    _seed_position(db, snapshot_id="p1", symbol="AAPL", quantity="1", average_cost="100")
    _seed_position(db, snapshot_id="p2", symbol="JNJ", quantity="10", average_cost="100")
    _seed_fundamentals(db, snapshot_id="f1", symbol="AAPL", sector="Technology")
    _seed_fundamentals(db, snapshot_id="f2", symbol="JNJ", sector="Healthcare")
    items = _client(db).get("/portfolio/sector-spread").json()["items"]
    assert items[0]["sector"].lower() == "healthcare"
    assert items[1]["sector"].lower() == "technology"


def test_unclassified_symbols_roll_into_onbekend(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_sync_run(db)
    _seed_position(db, snapshot_id="p1", symbol="AAPL", quantity="10", average_cost="100")
    _seed_position(db, snapshot_id="p2", symbol="MYSTERY", quantity="5", average_cost="100")
    _seed_fundamentals(db, snapshot_id="f1", symbol="AAPL", sector="Technology")
    # No fundamentals for MYSTERY.
    body = _client(db).get("/portfolio/sector-spread").json()
    labels = {item["sector"].lower() for item in body["items"]}
    assert "onbekend" in labels
    assert body["has_unclassified"] is True


def test_skips_zero_quantity_positions(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    _seed_sync_run(db)
    _seed_position(db, snapshot_id="p1", symbol="AAPL", quantity="10", average_cost="100")
    _seed_position(db, snapshot_id="p2", symbol="ZERO", quantity="0", average_cost="100")
    _seed_fundamentals(db, snapshot_id="f1", symbol="AAPL", sector="Technology")
    body = _client(db).get("/portfolio/sector-spread").json()
    assert body["total_positions"] == 1


def test_uses_only_latest_sync_run(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = _seed_db(tmp_path)
    # Older run holds JNJ; newer run holds AAPL — the response must
    # only contain AAPL.
    _seed_sync_run(db, sync_run_id="run-old")
    _seed_position(
        db, snapshot_id="p-old", symbol="JNJ", quantity="10",
        average_cost="50", sync_run_id="run-old",
    )
    _seed_sync_run(
        db, sync_run_id="run-new", started_at=_BASE_TS.replace(hour=10)
    )
    _seed_position(
        db, snapshot_id="p-new", symbol="AAPL", quantity="10",
        average_cost="100", sync_run_id="run-new",
    )
    _seed_fundamentals(db, snapshot_id="f1", symbol="AAPL", sector="Technology")
    _seed_fundamentals(db, snapshot_id="f2", symbol="JNJ", sector="Healthcare")
    body = _client(db).get("/portfolio/sector-spread").json()
    sectors = {item["sector"].lower() for item in body["items"]}
    assert "technology" in sectors
    assert "healthcare" not in sectors


def test_returns_dutch_help_text(tmp_path) -> None:  # type: ignore[no-untyped-def]
    body = _client(_seed_db(tmp_path)).get("/portfolio/sector-spread").json()
    assert "sector" in body["help_nl"].lower()
