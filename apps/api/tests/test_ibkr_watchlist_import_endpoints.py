from dataclasses import replace

from fastapi.testclient import TestClient

from portfolio_outlook_api.ibkr_watchlists import (
    IMPORT_CANDIDATES,
    IMPORT_RUNS,
    IbkrWatchlistInstrument,
    IbkrWatchlistSummary,
)
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings
from portfolio_outlook_api.watchlist import STORE, WatchlistItem


class FakeAdapter:
    def list_watchlists(self):
        return [
            IbkrWatchlistSummary(
                "wl-1",
                "USER_WATCHLIST",
                True,
                None,
                "USER_WATCHLIST",
                "ibkr_watchlist",
                "2026",
                None,
            )
        ]

    def list_instruments(self, watchlist_id: str):
        return [
            IbkrWatchlistInstrument(
                watchlist_id,
                "265598",
                "AAPL",
                "Apple",
                "STK",
                "NASDAQ",
                "NASDAQ",
                "USD",
                "imported",
                "candidate",
                "2026",
                None,
            ),
            IbkrWatchlistInstrument(
                watchlist_id,
                "999",
                "ASML",
                "ASML Holding",
                "STK",
                "AEB",
                "AEB",
                "EUR",
                "imported",
                "candidate",
                "2026",
                None,
            ),
            IbkrWatchlistInstrument(
                watchlist_id,
                None,
                "NOVAL",
                "No Conid",
                "STK",
                None,
                None,
                None,
                "imported",
                "candidate",
                "2026",
                None,
            ),
        ]


def _active_item(symbol: str, conid: str) -> WatchlistItem:
    return WatchlistItem(
        watchlist_item_id=f"watchlist-{symbol}",
        asset_id=None,
        symbol=symbol,
        name=symbol,
        exchange="NASDAQ",
        currency="USD",
        security_type="STK",
        note=None,
        status="active",
        source="manual",
        created_at="2026",
        updated_at="2026",
        ibkr_conid=conid,
        ibkr_symbol=symbol,
        ibkr_contract_name=symbol,
        ibkr_security_type="STK",
        ibkr_exchange="NASDAQ",
        ibkr_primary_exchange="NASDAQ",
        ibkr_currency="USD",
        ibkr_validation_status="valid",
        ibkr_validated_at="2026",
        ibkr_validation_source="ibkr_secdef_info",
    )


def test_watchlists_not_configured_safe_empty():
    client = TestClient(app)
    configured = replace(
        settings,
        ibkr_enabled=False,
        ibkr_gateway_url=None,
        ibkr_account_id_hint=None,
    )
    try:
        import portfolio_outlook_api.status_routes as routes

        routes.settings = configured
        body = client.get("/ibkr/watchlists").json()
        assert body["status"] == "not_configured"
        assert body["items"] == []
    finally:
        routes.settings = settings


def test_watchlist_import_preview_conflicts(monkeypatch):
    import portfolio_outlook_api.ibkr_watchlists as module

    monkeypatch.setattr(module, "DEFAULT_ADAPTER", FakeAdapter())
    STORE.clear()
    IMPORT_RUNS.clear()
    IMPORT_CANDIDATES.clear()
    STORE["existing"] = _active_item("AAPL", "265598")
    STORE["symbol-conflict"] = _active_item("ASML", "111")

    client = TestClient(app)
    body = client.get("/ibkr/watchlists").json()
    assert body["status"] == "ok"
    inst = client.get("/ibkr/watchlists/wl-1/instruments").json()
    assert len(inst["items"]) == 3

    imported = client.post("/ibkr/watchlists/wl-1/import").json()
    assert imported["status"] == "ok"
    statuses = {item["symbol"]: item["import_status"] for item in imported["candidates"]}
    assert statuses["AAPL"] == "already_in_local_watchlist"
    assert statuses["ASML"] == "needs_review"
    assert statuses["NOVAL"] == "skipped"

    latest = client.get("/ibkr/watchlists/imports/latest").json()
    assert latest["run"]["instrument_count"] == 3
    run_id = latest["run"]["import_run_id"]
    detail = client.get(f"/ibkr/watchlists/imports/{run_id}").json()
    assert len(detail["candidates"]) == 3
