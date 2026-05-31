"""Endpoint tests for ``GET/PUT /settings/market-events``."""

from __future__ import annotations

from fastapi.testclient import TestClient

from portfolio_outlook_api import market_events_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.market_events_routes import (
    settings as api_settings,
)

client = TestClient(app)


def _reset() -> None:
    api_settings.scheduler_per_market_close_digest_enabled = True
    api_settings.scheduler_per_market_open_alerts_enabled = False
    api_settings.universe_scan_index_codes = ""
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def test_returns_no_fires_when_no_universe_selected() -> None:
    r = client.get("/settings/market-events")
    body = r.json()
    assert r.status_code == 200
    assert body["per_market_close_digest_enabled"] is True
    assert body["per_market_open_alerts_enabled"] is False
    assert body["universe_codes_selected"] == []
    assert body["active_sessions"] == []
    assert body["fires"] == []


def test_returns_one_close_fire_for_euronext_when_bel20_selected() -> None:
    api_settings.universe_scan_index_codes = "BEL20"
    r = client.get("/settings/market-events")
    body = r.json()
    assert body["active_sessions"] == ["Euronext — Brussel, Amsterdam, Parijs"]
    assert len(body["fires"]) == 1
    fire = body["fires"][0]
    assert fire["market_code"] == "EURONEXT"
    assert fire["event_kind"] == "close"
    # Euronext close 17:30 + 15min buffer = 17:45 Europe/Brussels.
    assert fire["fire_hour"] == 17
    assert fire["fire_minute"] == 45
    assert fire["timezone"] == "Europe/Brussels"


def test_returns_two_fires_per_market_when_open_alerts_also_enabled() -> None:
    api_settings.universe_scan_index_codes = "BEL20"
    api_settings.scheduler_per_market_open_alerts_enabled = True
    r = client.get("/settings/market-events")
    body = r.json()
    kinds = sorted(f["event_kind"] for f in body["fires"])
    assert kinds == ["close", "open"]


def test_returns_fires_for_each_unique_session_in_universe() -> None:
    # BEL20 + AEX collapse to one Euronext session; DAX40 → Xetra;
    # SP100 → US_EQUITIES. Three sessions total, three close fires.
    api_settings.universe_scan_index_codes = "BEL20,AEX,DAX40,SP100"
    r = client.get("/settings/market-events")
    body = r.json()
    assert len(body["fires"]) == 3
    codes = sorted(f["market_code"] for f in body["fires"])
    assert codes == ["EURONEXT", "US_EQUITIES", "XETRA"]


def test_help_text_explains_legacy_replacement() -> None:
    r = client.get("/settings/market-events")
    body = r.json()
    # The help-text is the operator's first signal that the old
    # hourly-cron behavior has been retired; keep the test pinned to
    # that wording so the message can't silently drift away.
    assert "elk uur" in body["help_nl"].lower()
    assert "leeg" in body["help_nl"].lower() or "lege" in body["help_nl"].lower()


def test_close_fire_buffer_handles_us_session_close() -> None:
    api_settings.universe_scan_index_codes = "SP100"
    r = client.get("/settings/market-events")
    body = r.json()
    fire = body["fires"][0]
    assert fire["market_code"] == "US_EQUITIES"
    assert fire["timezone"] == "America/New_York"
    # 16:00 NY close + 15min buffer = 16:15 NY local.
    assert (fire["fire_hour"], fire["fire_minute"]) == (16, 15)


def test_locked_session_catalog_matches_worker_module() -> None:
    """Parity guard: the API's hard-coded session list must match the
    worker's locked catalog. If a session is added or removed in one
    place this test fails until both stay in sync."""

    from portfolio_outlook_worker.market_hours import locked_market_sessions

    api_codes = tuple(s.code for s in market_events_routes._LOCKED_SESSIONS)
    worker_codes = tuple(s.code for s in locked_market_sessions())
    assert api_codes == worker_codes, (
        "API and worker locked-session catalogs drifted; update both."
    )
