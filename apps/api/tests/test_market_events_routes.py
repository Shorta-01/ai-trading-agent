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


# ---------------------------------------------------------------------------
# /markets/hours-now — dashboard widget feed
# ---------------------------------------------------------------------------


def _at_utc(year: int, month: int, day: int, hour: int, minute: int) -> object:
    from datetime import UTC, datetime

    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def test_hours_now_returns_empty_markets_when_no_universe_selected() -> None:
    r = client.get("/markets/hours-now")
    body = r.json()
    assert r.status_code == 200
    assert body["universe_codes_selected"] == []
    assert body["markets"] == []
    assert "universe-scan" in body["help_nl"]


def test_hours_now_returns_one_entry_per_resolved_session(monkeypatch) -> None:
    """A universe with BEL20 + DAX40 resolves to two market sessions
    (Euronext + Xetra) — the widget gets one row per session, not per
    index code."""

    api_settings.universe_scan_index_codes = "BEL20,DAX40"
    # Mid-week, post-open: makes the assertions on state stable.
    monkeypatch.setattr(
        market_events_routes,
        "datetime",
        _PinnedDatetime(_at_utc(2026, 6, 3, 10, 0)),
    )
    r = client.get("/markets/hours-now")
    body = r.json()
    assert r.status_code == 200
    codes = [m["market_code"] for m in body["markets"]]
    assert codes == ["EURONEXT", "XETRA"]
    for m in body["markets"]:
        # Both Euronext + Xetra open 09:00 and close 17:30 local;
        # 10:00 UTC = 12:00 Brussels (CEST is UTC+2 in June).
        assert m["open_local_hhmm"] == "09:00"
        assert m["close_local_hhmm"] == "17:30"
        assert m["state"] == "open"
        assert m["next_event_kind"] == "close"


def test_hours_now_reports_pre_open_before_local_open(monkeypatch) -> None:
    api_settings.universe_scan_index_codes = "BEL20"
    # 06:00 UTC = 08:00 Brussels (CEST), before the 09:00 local open.
    monkeypatch.setattr(
        market_events_routes,
        "datetime",
        _PinnedDatetime(_at_utc(2026, 6, 3, 6, 0)),
    )
    body = client.get("/markets/hours-now").json()
    market = body["markets"][0]
    assert market["state"] == "pre_open"
    assert market["next_event_kind"] == "open"
    assert "Opent vandaag" in market["state_nl"]


def test_hours_now_reports_post_close_after_local_close(monkeypatch) -> None:
    api_settings.universe_scan_index_codes = "BEL20"
    # 18:00 UTC = 20:00 Brussels (CEST), after the 17:30 local close.
    monkeypatch.setattr(
        market_events_routes,
        "datetime",
        _PinnedDatetime(_at_utc(2026, 6, 3, 18, 0)),
    )
    body = client.get("/markets/hours-now").json()
    market = body["markets"][0]
    assert market["state"] == "post_close"
    assert market["next_event_kind"] == "open"


def test_hours_now_reports_weekend_when_local_date_is_saturday(monkeypatch) -> None:
    api_settings.universe_scan_index_codes = "BEL20"
    # 2026-06-06 is a Saturday.
    monkeypatch.setattr(
        market_events_routes,
        "datetime",
        _PinnedDatetime(_at_utc(2026, 6, 6, 10, 0)),
    )
    body = client.get("/markets/hours-now").json()
    market = body["markets"][0]
    assert market["state"] == "weekend"
    assert market["next_event_kind"] == "open"
    assert "weekend" in market["state_nl"].lower()


def test_hours_now_handles_us_session_with_correct_timezone(monkeypatch) -> None:
    api_settings.universe_scan_index_codes = "SP100"
    # 14:00 UTC = 10:00 EDT, NYSE is open (09:30 EDT open).
    monkeypatch.setattr(
        market_events_routes,
        "datetime",
        _PinnedDatetime(_at_utc(2026, 6, 3, 14, 0)),
    )
    body = client.get("/markets/hours-now").json()
    market = body["markets"][0]
    assert market["market_code"] == "US_EQUITIES"
    assert market["timezone"] == "America/New_York"
    assert market["open_local_hhmm"] == "09:30"
    assert market["close_local_hhmm"] == "16:00"
    assert market["state"] == "open"


class _PinnedDatetime:
    """Helper that swaps in a fixed ``datetime.now()`` while delegating
    every other attribute (UTC, timezone, etc.) to the real module so
    the rest of the code keeps working unchanged."""

    def __init__(self, fixed_now):
        from datetime import datetime as _real_datetime

        self._real = _real_datetime
        self._fixed = fixed_now

    def now(self, tz=None):  # noqa: ARG002 — matches the real signature
        return self._fixed

    def __getattr__(self, name):
        return getattr(self._real, name)
