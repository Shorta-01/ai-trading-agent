"""Tests for /settings/profit-target endpoints (V1.2 §AZ)."""

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
    db_path = str(tmp_path / "target.sqlite")
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


def _client(db_url: str) -> TestClient:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    return TestClient(app)


def _disable_storage() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def test_get_returns_doctrine_default_when_storage_disabled() -> None:
    _disable_storage()
    body = TestClient(app).get("/settings/profit-target").json()
    assert body["profit_target_pct"] == "4"
    assert body["is_doctrine_default"] is True


def test_get_returns_doctrine_default_when_no_runtime_config(tmp_path) -> None:  # type: ignore[no-untyped-def]
    body = _client(_seed_db(tmp_path)).get("/settings/profit-target").json()
    assert body["profit_target_pct"] == "4"
    assert body["is_doctrine_default"] is True


def test_put_persists_new_target(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    body = client.put(
        "/settings/profit-target", json={"profit_target_pct": "5.5"}
    ).json()
    assert body["is_doctrine_default"] is False
    assert body["profit_target_pct"].startswith("5.5")
    # Followup GET picks up the persisted value.
    after = client.get("/settings/profit-target").json()
    assert after["profit_target_pct"].startswith("5.5")
    assert after["is_doctrine_default"] is False


def test_put_null_resets_to_doctrine_default(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    client.put("/settings/profit-target", json={"profit_target_pct": "7"})
    body = client.put(
        "/settings/profit-target", json={"profit_target_pct": None}
    ).json()
    assert body["is_doctrine_default"] is True
    assert body["profit_target_pct"] == "4"


def test_put_rejects_below_minimum(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    response = client.put(
        "/settings/profit-target", json={"profit_target_pct": "0.5"}
    )
    assert response.status_code == 400


def test_put_rejects_above_maximum(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    response = client.put(
        "/settings/profit-target", json={"profit_target_pct": "75"}
    )
    assert response.status_code == 400


def test_put_rejects_garbage(tmp_path) -> None:  # type: ignore[no-untyped-def]
    client = _client(_seed_db(tmp_path))
    response = client.put(
        "/settings/profit-target", json={"profit_target_pct": "lots"}
    )
    assert response.status_code == 400


def test_belasting_uses_operator_target_for_hit_rate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """End-to-end: een operator-aangepast doel verandert de hit-rate
    in /belasting/jaaroverzicht."""

    db = _seed_db(tmp_path)
    client = _client(db)
    # Seed one trade that closes at ~9 % net — hit at default (4 %),
    # miss at custom 12 %.
    engine = create_engine(db, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO action_drafts ("
                "action_draft_id, decision_package_id, forecast_run_id, "
                "created_at, created_by, ibkr_account_id, conid, "
                "symbol, exchange, currency_local, side, quantity, "
                "order_type, limit_price_local, time_in_force, "
                "notional_local, notional_eur, fx_rate_at_creation, "
                "usable_cash_eur_at_creation, status, audit_trail_hash, "
                "safe_for_submission) VALUES "
                "('ad-1', NULL, NULL, '2026-01-10T15:00:00Z', 'user', "
                "'DU1', 'AAPL', 'AAPL', 'NASDAQ', 'USD', 'BUY', 10, "
                "'LMT', 100, 'DAY', 1000, 1000, 1, 50000, 'proposed', "
                "'h', 0)"
            )
        )
        for eid, side, price, ts in (
            ("b1", "BUY", "100", "2026-01-10T15:00:00Z"),
            ("s1", "SELL", "110", "2026-03-15T15:00:00Z"),
        ):
            conn.execute(
                text(
                    "INSERT INTO ibkr_executions ("
                    "ibkr_exec_id, ibkr_perm_id, action_draft_id, "
                    "account_id, conid, side, fill_price_local, "
                    "fill_quantity, fill_time, commission, "
                    "commission_currency, exchange) VALUES ("
                    f"'{eid}', {hash(eid) & 0x7FFFFFFF}, 'ad-1', 'DU1', "
                    f"'AAPL', '{side}', {price}, 10, '{ts}', 1, 'USD', "
                    "'NASDAQ')"
                )
            )
    engine.dispose()
    # Default target (4 %): hit-rate = 100 %.
    body_default = client.get("/belasting/jaaroverzicht?year=2026").json()
    assert body_default["year_totals"]["hit_rate_pct"] == 100.0
    # Custom 12 %: hit-rate = 0 %.
    client.put("/settings/profit-target", json={"profit_target_pct": "12"})
    body_custom = client.get("/belasting/jaaroverzicht?year=2026").json()
    assert body_custom["year_totals"]["hit_rate_pct"] == 0.0
