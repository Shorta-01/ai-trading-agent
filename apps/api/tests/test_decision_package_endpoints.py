"""Endpoint tests for the Decision Package routes."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset() -> None:
    api_settings.decision_packages_sync_enabled = False
    api_settings.suggestions_risk_profile = "Gebalanceerd"
    api_settings.decision_packages_valid_minutes = 1440
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def test_compute_blocked_when_disabled() -> None:
    r = client.post("/decision-packages/compute")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "decision_packages_sync_disabled"
    assert body["safe_for_action_drafts"] is False


def test_compute_blocked_when_storage_not_writable() -> None:
    api_settings.decision_packages_sync_enabled = True
    r = client.post("/decision-packages/compute")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def _fake_storage(
    monkeypatch,
    *,
    latest_run,
    positions,
    cash_snapshots,
    suggestions,
    forecasts,
    markets,
    fx_records,
    saved_target,
):
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

    class _List:
        def __init__(self, records: list[object]) -> None:
            self.records = records

    class _FakeIbkrRepo:
        def get_latest_ibkr_sync_run(self):
            return latest_run

        def list_ibkr_position_snapshots(self, _id: str):
            return positions

        def list_ibkr_account_cash_snapshots(self, _id: str):
            return cash_snapshots

        def list_latest_fx_rate_snapshots_by_pairs(self, _pairs: tuple[str, ...]):
            return fx_records

    class _FakeForecastRepo:
        def list_latest_asset_forecasts_by_conids(self, _conids):
            return _List(forecasts)

    class _FakeSuggestionRepo:
        def list_latest_asset_suggestions_by_conids(self, _conids):
            return _List(suggestions)

    class _FakeMarketRepo:
        def list_latest_market_data_snapshots_by_conids(self, _conids):
            return _List(markets)

    class _FakeDecisionPackageRepo:
        def save_asset_decision_package(self, record: object) -> object:
            saved_target.append(record)
            return None

        def list_latest_asset_decision_packages_by_conids(self, _conids):
            return _List(saved_target)

        def get_latest_asset_decision_package_by_conid(self, conid: str):
            for record in reversed(saved_target):
                if record.ibkr_conid == conid:
                    class _Read:
                        found = True
                        record_inner = record

                    class _ReadResult:
                        found = True
                        record_attr = record

                    return type(
                        "_ReadResult",
                        (),
                        {"found": True, "record": record},
                    )()
            return type("_ReadResult", (), {"found": False, "record": None})()

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: _FakeIbkrRepo(),
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
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyMarketDataSnapshotRepository",
        lambda *a, **k: _FakeMarketRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetDecisionPackageRepository",
        lambda *a, **k: _FakeDecisionPackageRepo(),
    )


def test_compute_blocked_when_no_positions(monkeypatch) -> None:
    api_settings.decision_packages_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    _fake_storage(
        monkeypatch,
        latest_run=None,
        positions=[],
        cash_snapshots=[],
        suggestions=[],
        forecasts=[],
        markets=[],
        fx_records=[],
        saved_target=[],
    )

    r = client.post("/decision-packages/compute")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "no_ibkr_sync_run"


def test_compute_runs_full_cycle_with_fake_repos(monkeypatch) -> None:
    api_settings.decision_packages_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.suggestions_risk_profile = "Gebalanceerd"

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
        quantity = Decimal("10")
        average_cost = Decimal("150")
        received_at = now
        stored_at = now

    class _Cash:
        snapshot_id = "c1"
        sync_run_id = "ibkr-sync-test"
        account_ref = "DU"
        base_currency = "USD"
        cash = Decimal("5000")
        available_funds = Decimal("4900")
        buying_power = Decimal("10000")
        received_at = now
        stored_at = now

    class _Suggestion:
        suggestion_id = "s1"
        ibkr_conid = "1"
        symbol = "AAPL"
        currency = "USD"
        forecast_id = "forecast_1"
        model_code = "baseline_label_translator"
        model_version = "v1.0.0"
        generated_at = now
        valid_until = now
        risk_profile = "Gebalanceerd"
        has_position = True
        action_label = "Houden"
        action_label_nl = "Houden"
        confidence_label = "Hoog"
        confidence_label_nl = "Hoog"
        confidence_score = Decimal("0.82")
        rationale_nl = "Rationale"
        drivers_json = ("direction=neutral",)
        blockers_json = None
        status = "ready"
        blocking_reason = None

    class _Forecast:
        forecast_id = "forecast_1"
        ibkr_conid = "1"
        symbol = "AAPL"
        currency = "USD"
        model_code = "baseline_gbm"
        model_version = "v1.0.0"
        horizon_days = 21
        generated_at = now
        valid_until = now
        data_points_used = 120
        history_first_bar_date = None
        history_last_bar_date = None
        current_price = Decimal("180")
        expected_return_pct = Decimal("1.1")
        p10_price = Decimal("170")
        p50_price = Decimal("182")
        p90_price = Decimal("194")
        prob_gain = Decimal("0.6")
        prob_loss = Decimal("0.4")
        prob_loss_gt_5pct = Decimal("0.1")
        prob_loss_gt_10pct = Decimal("0.02")
        prob_gain_gt_5pct = Decimal("0.25")
        prob_gain_gt_10pct = Decimal("0.08")
        expected_volatility_annual = Decimal("0.22")
        downside_risk_score = Decimal("5.5")
        confidence_score = Decimal("0.82")
        direction_label = "neutral"
        direction_label_nl = "Neutraal"
        explanation_nl = "test"
        status = "ready"
        blocking_reason = None

    class _Market:
        snapshot_id = "md1"
        ibkr_conid = "1"
        symbol = "AAPL"
        currency = "USD"
        asset_class = "STK"
        exchange = None
        primary_exchange = None
        provider_code = "eodhd"
        provider_environment = "real"
        provider_account_mode = "none"
        market_data_type = "eod"
        requested_at = now
        received_at = now
        provider_as_of = now
        stored_at = now
        last_price = Decimal("180")
        bid_price = None
        ask_price = None
        close_price = Decimal("180")
        day_change_percent = None
        status = "snapshot_available"
        freshness_status = "fresh"
        explanation_nl = "test"
        request_log_id = None
        provider_source_id = None
        freshness_audit_id = None

    saved: list[object] = []
    _fake_storage(
        monkeypatch,
        latest_run=_LatestRun(),
        positions=[_Pos()],
        cash_snapshots=[_Cash()],
        suggestions=[_Suggestion()],
        forecasts=[_Forecast()],
        markets=[_Market()],
        fx_records=[],
        saved_target=saved,
    )

    r = client.post("/decision-packages/compute")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "completed"
    assert body["package_total"] == 1
    assert body["package_persisted"] == 1
    assert body["safe_for_action_drafts"] is False
    assert body["safe_for_orders"] is False
    assert len(saved) == 1
    saved_record = saved[0]
    assert saved_record.suggestion_action_label == "Houden"
    assert saved_record.market_last_price == Decimal("180")


def test_latest_returns_not_configured_without_storage() -> None:
    r = client.get("/decision-packages/latest")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["items"] == []


def test_latest_for_conid_returns_not_configured_without_storage() -> None:
    r = client.get("/decision-packages/1/latest")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["item"] is None
