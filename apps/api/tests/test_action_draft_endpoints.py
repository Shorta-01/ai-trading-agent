"""Endpoint tests for the action-draft routes."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset() -> None:
    api_settings.action_drafts_sync_enabled = False
    api_settings.action_drafts_default_buy_value = "1000"
    api_settings.action_drafts_top_up_pct = "0.25"
    api_settings.action_drafts_reduce_pct = "0.25"
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def test_compute_blocked_when_disabled() -> None:
    r = client.post("/action-drafts/compute")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "action_drafts_sync_disabled"
    assert body["safe_for_submission"] is False
    assert body["safe_for_broker_submission"] is False


def test_compute_blocked_when_storage_not_writable() -> None:
    api_settings.action_drafts_sync_enabled = True
    r = client.post("/action-drafts/compute")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def _fake_storage(
    monkeypatch,
    *,
    latest_run,
    positions,
    cash_snapshots,
    packages,
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

    class _FakePackageRepo:
        def list_latest_asset_decision_packages_by_conids(self, _conids):
            return _List(packages)

    class _FakeDraftRepo:
        def save_asset_action_draft(self, record):
            saved_target.append(record)
            return None

        def list_latest_asset_action_drafts_by_conids(self, _conids):
            return _List(saved_target)

        def get_asset_action_draft_by_id(self, draft_id: str):
            for record in saved_target:
                if getattr(record, "draft_id", None) == draft_id:
                    return type("_Read", (), {"found": True, "record": record})()
            return type("_Read", (), {"found": False, "record": None})()

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
        "SqlAlchemyAssetDecisionPackageRepository",
        lambda *a, **k: _FakePackageRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetActionDraftRepository",
        lambda *a, **k: _FakeDraftRepo(),
    )


def test_compute_blocked_when_no_ibkr_sync(monkeypatch) -> None:
    api_settings.action_drafts_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    _fake_storage(
        monkeypatch,
        latest_run=None,
        positions=[],
        cash_snapshots=[],
        packages=[],
        saved_target=[],
    )

    r = client.post("/action-drafts/compute")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "no_ibkr_sync_run"


def test_compute_blocked_when_no_decision_packages(monkeypatch) -> None:
    api_settings.action_drafts_sync_enabled = True
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
        cash_snapshots=[],
        packages=[],
        saved_target=[],
    )

    r = client.post("/action-drafts/compute")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "no_decision_packages"


def test_compute_full_cycle_with_fake_repos(monkeypatch) -> None:
    api_settings.action_drafts_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.ibkr_expected_environment = "paper"

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
        quantity = Decimal("0")
        average_cost = None
        received_at = now
        stored_at = now

    class _Cash:
        snapshot_id = "c1"
        sync_run_id = "ibkr-sync-test"
        account_ref = "DU"
        base_currency = "USD"
        cash = Decimal("10000")
        available_funds = Decimal("9500")
        buying_power = Decimal("20000")
        received_at = now
        stored_at = now

    class _Package:
        decision_package_id = "dp-1"
        content_hash = "hash-1"
        ibkr_conid = "1"
        symbol = "AAPL"
        currency = "USD"
        risk_profile = "Gebalanceerd"
        generated_at = now
        valid_until = now
        position_snapshot_id = None
        position_quantity = Decimal("0")
        position_average_cost = None
        cash_snapshot_id = "c1"
        cash_base_currency = "USD"
        cash_amount = Decimal("10000")
        market_snapshot_id = "md1"
        market_last_price = Decimal("180")
        market_freshness_status = "fresh"
        market_provider_code = "eodhd"
        market_provider_as_of = now
        fx_pair = None
        fx_rate = None
        fx_freshness_status = None
        forecast_id = "forecast-1"
        forecast_model_code = "baseline_gbm"
        forecast_model_version = "v1.0.0"
        forecast_horizon_days = 21
        forecast_p10_price = Decimal("170")
        forecast_p50_price = Decimal("182")
        forecast_p90_price = Decimal("194")
        forecast_prob_gain = Decimal("0.6")
        forecast_prob_loss = Decimal("0.4")
        forecast_expected_return_pct = Decimal("1.1")
        forecast_expected_volatility_annual = Decimal("0.22")
        forecast_downside_risk_score = Decimal("5.5")
        forecast_confidence_score = Decimal("0.85")
        suggestion_id = "s1"
        suggestion_model_code = "baseline_label_translator"
        suggestion_action_label = "Kopen"
        suggestion_action_label_nl = "Kopen"
        suggestion_confidence_label = "Hoog"
        suggestion_confidence_label_nl = "Hoog"
        suggestion_status = "ready"
        has_position = False
        gate_outcomes_json = ()
        evidence_links_json = None
        audit_links_json = None
        rationale_nl = "rationale"
        explanation_nl = "explanation"
        status = "ready"
        blocking_reason = None

    saved: list[object] = []
    _fake_storage(
        monkeypatch,
        latest_run=_LatestRun(),
        positions=[_Pos()],
        cash_snapshots=[_Cash()],
        packages=[_Package()],
        saved_target=saved,
    )

    r = client.post("/action-drafts/compute")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "completed"
    assert body["draft_total"] == 1
    assert body["draft_persisted"] == 1
    assert body["dry_run_passed"] == 1
    assert body["safe_for_submission"] is False
    assert body["safe_for_orders"] is False
    assert body["safe_for_broker_submission"] is False
    assert len(saved) == 1
    assert saved[0].action_side == "BUY"
    assert saved[0].quantity == Decimal("5")


def test_latest_returns_not_configured_without_storage() -> None:
    r = client.get("/action-drafts/latest")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["items"] == []


def test_draft_by_id_returns_not_configured_without_storage() -> None:
    r = client.get("/action-drafts/foo")
    body = r.json()
    assert body["status"] == "not_configured"
    assert body["item"] is None
