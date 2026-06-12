"""Tests for the risk-limits (behavioural guardrail) settings API."""

from __future__ import annotations

from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app

client = TestClient(app)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.ibkr_account_id_hint = None


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _seed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = f"sqlite+pysqlite:///{tmp_path / 'risk_limits.sqlite'}"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    api_settings.ibkr_account_id_hint = "U1234567"
    engine = create_engine(db_url)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0071_orchestrator_scoring_verdicts')"
            )
        )


def test_get_returns_defaults(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    resp = client.get("/settings/risk-limits")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ibkr_account_id"] == "U1234567"
    # Brainstorm-locked defaults.
    assert body["daily_max_approvals"] == 5
    assert body["cooldown_seconds"] == 60
    assert body["anti_revenge_window_hours"] == 72
    assert body["soft_drawdown_window_days"] == 5
    assert body["hard_drawdown_window_days"] == 20
    # Decimals serialised as strings (no floats).
    assert body["anti_revenge_loss_threshold_pct"] == "1.0"
    assert body["soft_drawdown_pct"] == "5.0"
    assert body["hard_drawdown_pct"] == "10.0"
    assert body["fomo_drift_pct"] == "1.5"
    assert isinstance(body["soft_drawdown_pct"], str)


def test_put_changes_value_then_get_reflects_it(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    payload = {
        "daily_max_approvals": 3,
        "cooldown_seconds": 120,
        "anti_revenge_window_hours": 48,
        "anti_revenge_loss_threshold_pct": "2.5",
        "soft_drawdown_pct": "4.0",
        "soft_drawdown_window_days": 7,
        "hard_drawdown_pct": "12.0",
        "hard_drawdown_window_days": 25,
        "fomo_drift_pct": "2.0",
    }
    put = client.put("/settings/risk-limits", json=payload)
    assert put.status_code == 200
    saved = put.json()
    assert saved["daily_max_approvals"] == 3
    assert saved["anti_revenge_loss_threshold_pct"] == "2.5"

    # A fresh GET must reflect the persisted (committed) values.
    body = client.get("/settings/risk-limits").json()
    assert body["daily_max_approvals"] == 3
    assert body["cooldown_seconds"] == 120
    assert body["anti_revenge_window_hours"] == 48
    assert body["anti_revenge_loss_threshold_pct"] == "2.5"
    assert body["soft_drawdown_pct"] == "4.0"
    assert body["soft_drawdown_window_days"] == 7
    assert body["hard_drawdown_pct"] == "12.0"
    assert body["hard_drawdown_window_days"] == 25
    assert body["fomo_drift_pct"] == "2.0"


def test_put_invalid_value_returns_422(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    payload = {
        "daily_max_approvals": 0,  # must be positive -> ValueError -> 422
        "cooldown_seconds": 60,
        "anti_revenge_window_hours": 72,
        "anti_revenge_loss_threshold_pct": "1.0",
        "soft_drawdown_pct": "5.0",
        "soft_drawdown_window_days": 5,
        "hard_drawdown_pct": "10.0",
        "hard_drawdown_window_days": 20,
        "fomo_drift_pct": "1.5",
    }
    resp = client.put("/settings/risk-limits", json=payload)
    assert resp.status_code == 422
    assert "daily_max_approvals" in resp.json()["detail"]
