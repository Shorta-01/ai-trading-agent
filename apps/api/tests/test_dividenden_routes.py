"""Tests for /dividenden endpoints (V1.2 §BA)."""

from __future__ import annotations

import pytest
from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app


@pytest.fixture(autouse=True)
def _reset_storage_settings():  # type: ignore[no-untyped-def]
    original_enabled = api_settings.storage.enabled
    original_url = api_settings.storage.database_url
    original_writes = api_settings.storage.writes_enabled
    yield
    api_settings.storage.enabled = original_enabled
    api_settings.storage.database_url = original_url
    api_settings.storage.writes_enabled = original_writes


def _seed_db(tmp_path) -> str:  # type: ignore[no-untyped-def]
    db_path = str(tmp_path / "div.sqlite")
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
                "('0078_sell_signal_cards')"
            )
        )
    engine.dispose()
    return db_url


def _client(db_url: str) -> TestClient:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    return TestClient(app)


def _disable_storage() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def test_get_returns_empty_when_storage_disabled() -> None:
    _disable_storage()
    body = TestClient(app).get("/dividenden?year=2026").json()
    assert body["items"] == []
    assert body["treaty_defaults_pct_by_country"]["US"] == "15"


def test_get_returns_empty_when_no_dividends(tmp_path) -> None:  # type: ignore[no-untyped-def]
    body = _client(_seed_db(tmp_path)).get("/dividenden?year=2026").json()
    assert body["items"] == []
    assert body["totals"]["count"] == 0


def test_post_creates_dividend_with_treaty_default(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    response = client.post(
        "/dividenden",
        json={
            "symbol": "aapl",
            "pay_date": "2026-05-12",
            "currency_local": "USD",
            "gross_local": "100",
            "country_code": "us",
        },
    )
    assert response.status_code == 201
    body = client.get("/dividenden?year=2026").json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["symbol"] == "AAPL"
    assert item["country_code"] == "US"
    # 15 % default voor US.
    from decimal import Decimal as D

    assert D(item["withholding_pct"]) == D("15")
    assert D(item["withholding_local"]) == D("15")
    assert D(item["net_local"]) == D("85")


def test_post_accepts_custom_withholding(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from decimal import Decimal as D

    client = _client(_seed_db(tmp_path))
    client.post(
        "/dividenden",
        json={
            "symbol": "TTE",
            "pay_date": "2026-05-12",
            "currency_local": "EUR",
            "gross_local": "100",
            "country_code": "FR",
            "withholding_pct": "10",
        },
    )
    body = client.get("/dividenden?year=2026").json()
    assert D(body["items"][0]["withholding_pct"]) == D("10")


def test_post_rejects_invalid_withholding(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    response = client.post(
        "/dividenden",
        json={
            "symbol": "X",
            "pay_date": "2026-05-12",
            "currency_local": "USD",
            "gross_local": "100",
            "withholding_pct": "150",
        },
    )
    assert response.status_code == 400


def test_post_rejects_bad_date(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    response = client.post(
        "/dividenden",
        json={
            "symbol": "X",
            "pay_date": "12-05-2026",
            "currency_local": "USD",
            "gross_local": "100",
        },
    )
    assert response.status_code == 400


def test_delete_removes_dividend(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    client.post(
        "/dividenden",
        json={
            "symbol": "AAPL",
            "pay_date": "2026-05-12",
            "currency_local": "USD",
            "gross_local": "100",
            "country_code": "US",
        },
    )
    listed = client.get("/dividenden?year=2026").json()
    dividend_id = listed["items"][0]["dividend_event_id"]
    response = client.delete(f"/dividenden/{dividend_id}")
    assert response.status_code == 200
    after = client.get("/dividenden?year=2026").json()
    assert after["items"] == []


def test_kpis_aggregate_per_currency(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    for symbol, ccy, country, gross in (
        ("AAPL", "USD", "US", "100"),
        ("MSFT", "USD", "US", "50"),
        ("TTE", "EUR", "FR", "200"),
    ):
        client.post(
            "/dividenden",
            json={
                "symbol": symbol,
                "pay_date": "2026-05-12",
                "currency_local": ccy,
                "gross_local": gross,
                "country_code": country,
            },
        )
    body = client.get("/dividenden?year=2026").json()
    totals = body["totals"]
    assert totals["count"] == 3
    assert totals["gross_by_currency"]["USD"] == "150.00"
    assert totals["gross_by_currency"]["EUR"] == "200.00"
    assert totals["net_by_currency"]["USD"] == "127.50"  # 150 - (150*0.15)


def test_belasting_endpoint_surfaces_dividends(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """End-to-end: dividenden door /belasting jaaroverzicht."""

    client = _client(_seed_db(tmp_path))
    client.post(
        "/dividenden",
        json={
            "symbol": "AAPL",
            "pay_date": "2026-05-12",
            "currency_local": "USD",
            "gross_local": "100",
            "country_code": "US",
        },
    )
    body = client.get("/belasting/jaaroverzicht?year=2026").json()
    assert len(body["dividends"]) == 1
    assert body["dividends"][0]["symbol"] == "AAPL"


def test_get_filters_per_year(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    for year_str in ("2025-05-12", "2026-05-12"):
        client.post(
            "/dividenden",
            json={
                "symbol": "AAPL",
                "pay_date": year_str,
                "currency_local": "USD",
                "gross_local": "100",
                "country_code": "US",
            },
        )
    body_2025 = client.get("/dividenden?year=2025").json()
    body_2026 = client.get("/dividenden?year=2026").json()
    assert len(body_2025["items"]) == 1
    assert len(body_2026["items"]) == 1
