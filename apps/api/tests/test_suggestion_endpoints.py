"""Endpoint tests for ``POST /suggestions/compute`` and ``GET /suggestions/latest``."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset() -> None:
    api_settings.suggestions_sync_enabled = False
    api_settings.suggestions_risk_profile = "Gebalanceerd"
    api_settings.suggestions_valid_minutes = 1440
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def test_compute_blocked_when_disabled() -> None:
    r = client.post("/suggestions/compute")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "suggestions_sync_disabled"
    assert body["safe_for_orders"] is False


def test_compute_blocked_when_storage_not_writable() -> None:
    api_settings.suggestions_sync_enabled = True
    r = client.post("/suggestions/compute")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def _fake_storage(monkeypatch, *, latest_run, positions, forecasts, saved_target):
    class _Connection:
        connection = "fake"
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Connection()

        def __exit__(self, *_):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    class _ListResult:
        def __init__(self, records: list[object]) -> None:
            self.records = records

    class _FakeIbkr:
        def get_latest_ibkr_sync_run(self):
            return latest_run

        def list_ibkr_position_snapshots(self, _id: str):
            return positions

    class _FakeForecastRepo:
        def list_latest_asset_forecasts_by_conids(self, _conids: tuple[str, ...]):
            return _ListResult(forecasts)

    class _FakeSuggestionRepo:
        def save_asset_suggestion(self, record: object) -> object:
            saved_target.append(record)
            return None

        def expire_stale_asset_suggestions(self, *, now: object) -> int:
            return 0

        def list_latest_asset_suggestions_by_conids(self, _conids: tuple[str, ...]):
            return _ListResult(saved_target)

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: _FakeIbkr(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetForecastRepository",
        lambda *a, **k: _FakeForecastRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetSuggestionRepository",
        lambda *a, **k: _FakeSuggestionRepo(),
    )


def test_compute_blocked_when_no_positions(monkeypatch) -> None:
    api_settings.suggestions_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    _fake_storage(
        monkeypatch, latest_run=None, positions=[], forecasts=[], saved_target=[]
    )

    r = client.post("/suggestions/compute")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "no_positions"


def test_compute_blocked_when_no_forecasts(monkeypatch) -> None:
    api_settings.suggestions_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    now = datetime(2025, 5, 24, tzinfo=UTC)

    class _LatestRun:
        sync_run_id = "ibkr-sync-test"

    class _Pos:
        snapshot_id = "p1"
        sync_run_id = "ibkr-sync-test"
        account_ref = "DU"
        conid = "1"
        symbol = "AAPL"
        security_type = "STK"
        currency = "USD"
        exchange = "SMART"
        primary_exchange = "NASDAQ"
        quantity = Decimal("5")
        average_cost = Decimal("90")
        received_at = now
        stored_at = now

    _fake_storage(
        monkeypatch,
        latest_run=_LatestRun(),
        positions=[_Pos()],
        forecasts=[],
        saved_target=[],
    )

    r = client.post("/suggestions/compute")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "no_forecasts"


def test_compute_runs_full_cycle_with_fake_repos(monkeypatch) -> None:
    api_settings.suggestions_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.suggestions_risk_profile = "Groei"

    now = datetime(2025, 5, 24, tzinfo=UTC)

    class _LatestRun:
        sync_run_id = "ibkr-sync-test"

    class _Pos:
        snapshot_id = "p1"
        sync_run_id = "ibkr-sync-test"
        account_ref = "DU"
        conid = "1"
        symbol = "AAPL"
        security_type = "STK"
        currency = "USD"
        exchange = "SMART"
        primary_exchange = "NASDAQ"
        quantity = Decimal("5")
        average_cost = Decimal("90")
        received_at = now
        stored_at = now

    class _Forecast:
        forecast_id = "forecast_x"
        ibkr_conid = "1"
        symbol = "AAPL"
        currency = "USD"
        model_code = "baseline_gbm"
        model_version = "v1.0.0"
        horizon_days = 21
        generated_at = now
        valid_until = now
        data_points_used = 200
        history_first_bar_date = date(2025, 1, 1)
        history_last_bar_date = date(2025, 5, 23)
        current_price = Decimal("180")
        expected_return_pct = Decimal("3.0")
        p10_price = Decimal("160")
        p50_price = Decimal("185")
        p90_price = Decimal("210")
        prob_gain = Decimal("0.70")
        prob_loss = Decimal("0.30")
        prob_loss_gt_5pct = Decimal("0.10")
        prob_loss_gt_10pct = Decimal("0.02")
        prob_gain_gt_5pct = Decimal("0.50")
        prob_gain_gt_10pct = Decimal("0.25")
        expected_volatility_annual = Decimal("0.22")
        downside_risk_score = Decimal("8.5")
        confidence_score = Decimal("0.85")
        direction_label = "strong_up"
        direction_label_nl = "Sterke stijging verwacht"
        explanation_nl = "test"
        status = "ready"
        blocking_reason = None

    saved: list[object] = []
    _fake_storage(
        monkeypatch,
        latest_run=_LatestRun(),
        positions=[_Pos()],
        forecasts=[_Forecast()],
        saved_target=saved,
    )

    r = client.post("/suggestions/compute")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "completed"
    assert body["suggestion_total"] == 1
    assert body["suggestion_persisted"] == 1
    assert body["held_positions"] == 1
    assert body["cold_start_positions"] == 0
    assert body["risk_profile"] == "Groei"
    assert body["safe_for_orders"] is False
    assert body["safe_for_action_drafts"] is False
    assert len(saved) == 1
    saved_record = saved[0]
    # Held + strong_up + high confidence on Groei → Langzaam bijkopen.
    assert saved_record.action_label == "Langzaam bijkopen"


def test_latest_returns_not_configured_without_storage() -> None:
    r = client.get("/suggestions/latest")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["items"] == []
    assert body["safe_for_orders"] is False
