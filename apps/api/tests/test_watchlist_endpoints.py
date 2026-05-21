from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app
from portfolio_outlook_api.watchlist import STORE

client = TestClient(app)


def setup_function() -> None:
    STORE.clear()


def _valid_payload() -> dict[str, str]:
    return {
        "ibkr_conid": "265598",
        "ibkr_symbol": "aapl",
        "ibkr_contract_name": "Apple Inc",
        "ibkr_security_type": "STK",
        "ibkr_exchange": "SMART",
        "ibkr_primary_exchange": "NASDAQ",
        "ibkr_currency": "USD",
        "ibkr_validation_status": "valid",
    }


def _enable_storage_for_asset_listing(monkeypatch) -> None:
    monkeypatch.setattr("portfolio_outlook_api.watchlist.settings.storage.enabled", True)
    monkeypatch.setattr(
        "portfolio_outlook_api.watchlist.settings.storage.database_url",
        "sqlite:///:memory:",
    )


def test_watchlist_create_requires_validated_ibkr_contract() -> None:
    bad = client.post("/watchlist/items", json={"symbol": "ASML"})
    assert bad.status_code == 422

    no_valid = client.post(
        "/watchlist/items", json={**_valid_payload(), "ibkr_validation_status": "not_found"}
    )
    assert no_valid.status_code == 422

    created = client.post(
        "/watchlist/items", json={**_valid_payload(), "note": "kernpositie volgen"}
    )
    assert created.status_code == 200
    wrapped = created.json()["item"]
    item = wrapped["item"]
    assert item["symbol"] == "AAPL"
    assert item["ibkr_conid"] == "265598"
    assert wrapped["ibkr_status_label_nl"] == "Gevalideerd"
    assert wrapped["analysis_readiness_label_nl"] == "Klaar voor latere data-opbouw"


def test_watchlist_duplicate_ibkr_contract_is_blocked() -> None:
    first = client.post("/watchlist/items", json=_valid_payload())
    assert first.status_code == 200
    dup = client.post("/watchlist/items", json=_valid_payload())
    assert dup.status_code == 409


def test_patch_watchlist_item_links_asset_and_unlinks(monkeypatch) -> None:
    created = client.post("/watchlist/items", json=_valid_payload())
    item_id = created.json()["item"]["item"]["watchlist_item_id"]

    def fake_resolve(asset_id: str | None, *, fail_if_missing: bool):
        if asset_id is None:
            return None
        return {
            "asset_id": "asset-1",
            "canonical_symbol": "AAPL",
            "asset_name": "Apple",
            "primary_exchange": "NASDAQ",
            "primary_currency": "USD",
        }

    monkeypatch.setattr("portfolio_outlook_api.watchlist._resolve_asset_summary", fake_resolve)

    linked = client.patch(f"/watchlist/items/{item_id}", json={"asset_id": "asset-1"})
    assert linked.status_code == 200
    payload = linked.json()["item"]
    assert payload["item"]["asset_id"] == "asset-1"
    assert payload["link_status"] == "gelinkt"

    unlinked = client.patch(f"/watchlist/items/{item_id}", json={"asset_id": None})
    assert unlinked.status_code == 200
    assert unlinked.json()["item"]["item"]["asset_id"] is None


def test_watchlist_asset_listing_missing(monkeypatch) -> None:
    created = client.post("/watchlist/items", json=_valid_payload())
    assert created.status_code == 200

    _enable_storage_for_asset_listing(monkeypatch)
    monkeypatch.setattr("portfolio_outlook_api.watchlist._with_repository", lambda op: None)
    payload = client.get("/watchlist/items").json()["items"][0]
    readiness = payload["asset_listing_readiness"]
    assert readiness["link_status"] == "missing_listing"
    assert readiness["analysis_ready"] is False
    assert readiness["suggestions_allowed"] is False
    assert readiness["action_drafts_allowed"] is False
    assert "market-data/analysestappen" in readiness["next_step_nl"]
    assert "market_price" not in payload
    assert "recommendation" not in payload


def test_watchlist_asset_listing_unvalidated(monkeypatch) -> None:
    created = client.post("/watchlist/items", json=_valid_payload())
    assert created.status_code == 200
    _enable_storage_for_asset_listing(monkeypatch)

    class Listing:
        listing_id = "lst-1"
        asset_id = "asset-1"
        ibkr_conid = "265598"
        symbol = "AAPL"
        security_type = "STK"
        exchange = "SMART"
        primary_exchange = "NASDAQ"
        currency = "USD"
        validation_status = "unvalidated"
        validated_at = None
        safe_to_use_for_market_data = False

    monkeypatch.setattr("portfolio_outlook_api.watchlist._with_repository", lambda op: Listing())
    readiness = client.get("/watchlist/items").json()["items"][0]["asset_listing_readiness"]
    assert readiness["link_status"] == "unvalidated_listing"
    assert readiness["blocker_code"] == "listing_not_validated_or_safe"
    assert readiness["analysis_ready"] is False
    assert readiness["suggestions_allowed"] is False
    assert readiness["action_drafts_allowed"] is False


def test_watchlist_asset_listing_validated_still_blocked_for_runtime(monkeypatch) -> None:
    created = client.post("/watchlist/items", json=_valid_payload())
    assert created.status_code == 200
    _enable_storage_for_asset_listing(monkeypatch)

    class Listing:
        listing_id = "lst-2"
        asset_id = "asset-1"
        ibkr_conid = "265598"
        symbol = "AAPL"
        security_type = "STK"
        exchange = "SMART"
        primary_exchange = "NASDAQ"
        currency = "USD"
        validation_status = "valid"
        validated_at = None
        safe_to_use_for_market_data = True

    monkeypatch.setattr("portfolio_outlook_api.watchlist._with_repository", lambda op: Listing())
    readiness = client.get("/watchlist/items").json()["items"][0]["asset_listing_readiness"]
    assert readiness["link_status"] == "validated_listing"
    assert readiness["market_data_ready"] is False
    assert readiness["analysis_ready"] is False
    assert readiness["suggestions_allowed"] is False
    assert readiness["action_drafts_allowed"] is False
    assert "runtime" in readiness["next_step_nl"]


def test_watchlist_asset_listing_storage_unavailable(monkeypatch) -> None:
    created = client.post("/watchlist/items", json=_valid_payload())
    assert created.status_code == 200

    monkeypatch.setattr("portfolio_outlook_api.watchlist.settings.storage.enabled", False)
    readiness = client.get("/watchlist/items").json()["items"][0]["asset_listing_readiness"]
    assert readiness["link_status"] == "storage_unavailable"
    watchlist_item_id = created.json()["item"]["item"]["watchlist_item_id"]
    detail_response = client.get(f"/watchlist/items/{watchlist_item_id}")
    detail = detail_response.json()["item"]["asset_listing_readiness"]
    assert detail["link_status"] == "storage_unavailable"
