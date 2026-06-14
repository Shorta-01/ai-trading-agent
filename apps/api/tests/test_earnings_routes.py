"""Tests for the earnings upcoming endpoint (V1.2 §AI)."""

from __future__ import annotations

import json  # noqa: F401  - used by some seeded payloads in earlier tests
from datetime import UTC, date, datetime, timedelta

from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "earnings.sqlite")
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
                "('0077_monthly_report_archive')"
            )
        )
    engine.dispose()
    return db_url


def _insert_event(
    db_url: str,
    *,
    earnings_event_id: str,
    symbol: str = "AAPL",
    event_date: date = date(2026, 6, 19),
    status: str = "confirmed",
) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO earnings_events ("
                "earnings_event_id, symbol, ibkr_conid, event_date, "
                "status, source, fetched_at, raw_json) VALUES ("
                ":eid, :sym, '1', :ed, :st, 'eodhd', "
                ":fa, :raw)"
            ),
            {
                "eid": earnings_event_id,
                "sym": symbol,
                "ed": event_date.isoformat(),
                "st": status,
                "fa": datetime(2026, 6, 12, 6, 0, tzinfo=UTC).isoformat(),
                "raw": json.dumps({"eps_estimate": "1.5"}),
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


def test_upcoming_empty_when_storage_disabled() -> None:
    _disable_storage()
    client = TestClient(app)
    response = client.get("/earnings/upcoming")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["window_days"] == 14


def test_upcoming_empty_when_no_events(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.get("/earnings/upcoming")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_upcoming_returns_events_within_window(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    today = datetime.now(tz=UTC).date()
    _insert_event(
        db_url, earnings_event_id="ev-1", symbol="AAPL",
        event_date=today + timedelta(days=3),
    )
    _insert_event(
        db_url, earnings_event_id="ev-2", symbol="MSFT",
        event_date=today + timedelta(days=10),
    )
    # Outside default 14-day window:
    _insert_event(
        db_url, earnings_event_id="ev-3", symbol="LATER",
        event_date=today + timedelta(days=30),
    )
    client = _client(db_url)
    response = client.get("/earnings/upcoming")
    assert response.status_code == 200
    items = response.json()["items"]
    symbols = [item["symbol"] for item in items]
    assert symbols == ["AAPL", "MSFT"]


def test_upcoming_respects_days_param(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    today = datetime.now(tz=UTC).date()
    _insert_event(
        db_url, earnings_event_id="ev-1", symbol="AAPL",
        event_date=today + timedelta(days=30),
    )
    client = _client(db_url)
    body = client.get("/earnings/upcoming?days=45").json()
    assert body["window_days"] == 45
    assert [item["symbol"] for item in body["items"]] == ["AAPL"]


def test_upcoming_caps_days_at_60(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    body = client.get("/earnings/upcoming?days=9999").json()
    assert body["window_days"] == 60


def test_upcoming_rejects_non_positive_days(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.get("/earnings/upcoming?days=0")
    assert response.status_code == 400


def test_upcoming_skips_past_events(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    today = datetime.now(tz=UTC).date()
    _insert_event(
        db_url, earnings_event_id="ev-past", symbol="OLD",
        event_date=today + timedelta(days=3),
        status="past",
    )
    client = _client(db_url)
    body = client.get("/earnings/upcoming").json()
    assert body["items"] == []


# ---- POST /earnings/refresh (V1.2 §AJ) ----


def test_refresh_skipped_when_storage_disabled() -> None:
    _disable_storage()
    client = TestClient(app)
    response = client.post(
        "/earnings/refresh", json={"symbols": ["AAPL.US"], "window_days": 21}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "skipped"
    assert "Opslag" in (body.get("error_text") or "")


def test_refresh_skipped_when_eodhd_key_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    api_settings.eodhd_api_key = None
    client = _client(db_url)
    response = client.post(
        "/earnings/refresh", json={"symbols": ["AAPL.US"], "window_days": 21}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "skipped"
    assert "EODHD" in (body.get("error_text") or "")


def test_refresh_rejects_empty_symbols(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.post(
        "/earnings/refresh", json={"symbols": [], "window_days": 21}
    )
    assert response.status_code == 400


def test_refresh_rejects_non_positive_window_days(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    client = _client(db_url)
    response = client.post(
        "/earnings/refresh", json={"symbols": ["AAPL.US"], "window_days": 0}
    )
    assert response.status_code == 400


def test_refresh_with_key_and_storage_runs_end_to_end(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    db_url = _seed_db(tmp_path)
    api_settings.eodhd_api_key = "test-key"
    client = _client(db_url)

    # Patch the EodhdClient constructor on the route module so we
    # never make a real HTTP call.
    from portfolio_outlook_api import earnings_routes as routes_module

    class _StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def fetch_earnings_calendar(self, *, symbols, from_date, to_date):
            from portfolio_outlook_api.eodhd_client import EodhdEarningsEvent

            return [
                EodhdEarningsEvent(
                    symbol="AAPL.US",
                    event_date=date(2026, 7, 30),
                    status="confirmed",
                    raw_payload={"eps_estimate": "1.45"},
                ),
            ]

    monkeypatch.setattr(routes_module, "EodhdClient", _StubClient)
    response = client.post(
        "/earnings/refresh",
        json={"symbols": ["AAPL.US"], "window_days": 21},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["fetched_count"] == 1
    assert body["upserted_count"] == 1
    assert body["error_text"] is None
