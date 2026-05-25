"""Endpoint tests for ``GET /v1/release-readiness`` (Slices 22 + 34)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.eodhd_enabled = False
    api_settings.eodhd_api_key = None
    api_settings.ibkr_enabled = False
    api_settings.ibkr_sync_enabled = False
    api_settings.scheduler_enabled = False
    api_settings.market_data_sync_enabled = False
    api_settings.forecast_sync_enabled = False
    api_settings.suggestions_sync_enabled = False
    api_settings.decision_packages_sync_enabled = False
    api_settings.action_drafts_sync_enabled = False
    api_settings.daily_briefing_sync_enabled = False
    api_settings.reconciliation_sync_enabled = False
    api_settings.prediction_diary_sync_enabled = False
    api_settings.ensemble_weight_strategy = "equal_weight"
    api_settings.predictor_backtest_enabled = False
    api_settings.universe_set = "SP500"
    api_settings.ai_explanation_real_client_enabled = False
    api_settings.ai_ts_predictor_real_client_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def test_endpoint_returns_blocked_by_default() -> None:
    r = client.get("/v1/release-readiness")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert len(body["blockers"]) >= 10
    assert body["safe_for_orders"] is False
    assert body["blocks_orders"] is True


def test_endpoint_returns_ready_when_every_flag_is_set() -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.eodhd_enabled = True
    api_settings.eodhd_api_key = "key-123"
    api_settings.ibkr_enabled = True
    api_settings.ibkr_sync_enabled = True
    api_settings.scheduler_enabled = True
    api_settings.market_data_sync_enabled = True
    api_settings.forecast_sync_enabled = True
    api_settings.suggestions_sync_enabled = True
    api_settings.decision_packages_sync_enabled = True
    api_settings.action_drafts_sync_enabled = True
    api_settings.daily_briefing_sync_enabled = True
    api_settings.reconciliation_sync_enabled = True
    api_settings.prediction_diary_sync_enabled = True
    api_settings.ensemble_weight_strategy = "auto"
    api_settings.predictor_backtest_enabled = True
    api_settings.universe_set = "SP500"

    r = client.get("/v1/release-readiness")
    body = r.json()
    assert body["status"] == "ready"
    assert body["blockers"] == []
    assert body["safe_for_orders"] is False  # never flips, even when ready
    assert "klaar voor productie" in body["summary_nl"]


def test_endpoint_surfaces_individual_blocker_when_one_flag_is_off() -> None:
    # Turn everything on except the scheduler.
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.eodhd_enabled = True
    api_settings.eodhd_api_key = "key-123"
    api_settings.ibkr_enabled = True
    api_settings.ibkr_sync_enabled = True
    api_settings.market_data_sync_enabled = True
    api_settings.forecast_sync_enabled = True
    api_settings.suggestions_sync_enabled = True
    api_settings.decision_packages_sync_enabled = True
    api_settings.action_drafts_sync_enabled = True
    api_settings.daily_briefing_sync_enabled = True
    api_settings.reconciliation_sync_enabled = True
    api_settings.prediction_diary_sync_enabled = True
    api_settings.ensemble_weight_strategy = "auto"
    api_settings.predictor_backtest_enabled = True
    api_settings.universe_set = "SP500"
    api_settings.scheduler_enabled = False

    r = client.get("/v1/release-readiness")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["blockers"] == ["scheduler_disabled"]
