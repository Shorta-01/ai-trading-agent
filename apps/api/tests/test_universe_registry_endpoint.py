"""Endpoint tests for `GET /universe/registry` (V1.1 Slice 31)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset() -> None:
    api_settings.universe_set = "SP500"


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def test_registry_default_returns_sp500_entries() -> None:
    r = client.get("/universe/registry")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert body["set_code"] == "SP500"
    assert body["configured_set"] == "SP500"
    assert "EU600" in body["available_sets"]
    assert body["entry_count"] > 0
    assert body["items"][0]["eodhd_symbol"]
    assert body["safe_for_orders"] is False


def test_registry_eu600_set_includes_uk_swiss_names() -> None:
    r = client.get("/universe/registry?set_code=EU600")
    body = r.json()
    assert body["set_code"] == "EU600"
    symbols = [item["eodhd_symbol"] for item in body["items"]]
    assert "AZN.LSE" in symbols
    assert "NESN.SW" in symbols
    assert body["entry_count"] > 0


def test_registry_all_5k_strictly_supersets_eu600() -> None:
    eu = client.get("/universe/registry?set_code=EU600").json()
    all_ = client.get("/universe/registry?set_code=ALL_5K").json()
    eu_set = {item["eodhd_symbol"] for item in eu["items"]}
    all_set = {item["eodhd_symbol"] for item in all_["items"]}
    assert eu_set < all_set


def test_registry_returns_blocked_for_unknown_set() -> None:
    r = client.get("/universe/registry?set_code=BOGUS")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["items"] == []
    assert "BOGUS" in body["help_nl"]


def test_registry_falls_back_to_configured_set_when_query_omitted() -> None:
    api_settings.universe_set = "EU600"
    r = client.get("/universe/registry")
    body = r.json()
    assert body["set_code"] == "EU600"
    assert body["configured_set"] == "EU600"


def test_registry_country_code_field_present_on_items() -> None:
    r = client.get("/universe/registry?set_code=EU600")
    body = r.json()
    # At least one EU600 entry should carry a country code (the V1.1
    # §22.4 addition).
    countries = [
        item["country_code"] for item in body["items"] if item.get("country_code")
    ]
    assert "GB" in countries
    assert "CH" in countries
