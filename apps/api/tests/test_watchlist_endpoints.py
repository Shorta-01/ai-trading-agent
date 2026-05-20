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
