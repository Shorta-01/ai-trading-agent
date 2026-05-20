from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app
from portfolio_outlook_api.watchlist import STORE

client = TestClient(app)


def setup_function() -> None:
    STORE.clear()


def test_watchlist_crud_flow() -> None:
    empty = client.get("/watchlist/items")
    assert empty.status_code == 200
    assert empty.json()["items"] == []

    created = client.post(
        "/watchlist/items",
        json={"symbol": " asml ", "note": "kernpositie volgen"},
    )
    assert created.status_code == 200
    item_wrapper = created.json()["item"]
    item = item_wrapper["item"]
    assert item["symbol"] == "ASML"
    assert item_wrapper["link_status"] == "niet_gelinkt"

    get_one = client.get(f"/watchlist/items/{item['watchlist_item_id']}")
    assert get_one.status_code == 200

    dup = client.post("/watchlist/items", json={"symbol": "ASML"})
    assert dup.status_code == 409

    updated = client.patch(
        f"/watchlist/items/{item['watchlist_item_id']}",
        json={"note": "bijgewerkt"},
    )
    assert updated.status_code == 200
    assert updated.json()["item"]["item"]["note"] == "bijgewerkt"

    archived = client.delete(f"/watchlist/items/{item['watchlist_item_id']}")
    assert archived.status_code == 200

    listed = client.get("/watchlist/items")
    assert listed.json()["items"] == []


def test_patch_watchlist_item_links_asset_and_unlinks(monkeypatch) -> None:
    created = client.post("/watchlist/items", json={"symbol": "ASML"})
    item_id = created.json()["item"]["item"]["watchlist_item_id"]

    def fake_resolve(asset_id: str | None, *, fail_if_missing: bool):
        if asset_id is None:
            return None
        return {
            "asset_id": "asset-1",
            "canonical_symbol": "ASML",
            "asset_name": "ASML Holding",
            "primary_exchange": "AEB",
            "primary_currency": "EUR",
        }

    monkeypatch.setattr("portfolio_outlook_api.watchlist._resolve_asset_summary", fake_resolve)

    linked = client.patch(f"/watchlist/items/{item_id}", json={"asset_id": "asset-1"})
    assert linked.status_code == 200
    payload = linked.json()["item"]
    assert payload["item"]["asset_id"] == "asset-1"
    assert payload["link_status"] == "gelinkt"
    assert payload["linked_asset"]["canonical_symbol"] == "ASML"

    unlinked = client.patch(f"/watchlist/items/{item_id}", json={"asset_id": None})
    assert unlinked.status_code == 200
    assert unlinked.json()["item"]["item"]["asset_id"] is None


def test_patch_watchlist_item_rejects_missing_asset_identity() -> None:
    created = client.post("/watchlist/items", json={"symbol": "ASML"})
    item_id = created.json()["item"]["item"]["watchlist_item_id"]

    bad = client.patch(f"/watchlist/items/{item_id}", json={"asset_id": "asset-missing"})
    assert bad.status_code == 422
