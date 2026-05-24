"""Endpoint tests for the daily briefing routes (Slice 12)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    BriefingAlertRecord,
    DailyBriefingRecord,
    IbkrSyncRunRecord,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_NOW = datetime(2025, 5, 24, 9, 0, tzinfo=UTC)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.daily_briefing_sync_enabled = False
    api_settings.daily_briefing_lookback_hours = 24


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _sync_run() -> IbkrSyncRunRecord:
    return IbkrSyncRunRecord(
        sync_run_id="run-1",
        started_at=_NOW - timedelta(minutes=1),
        completed_at=_NOW,
        provider_code="ibkr",
        provider_environment="paper",
        account_mode="paper",
        readonly=True,
        status="ok",
        account_summary_status="ok",
        positions_status="ok",
        open_orders_status="ok",
        executions_status="ok",
        positions_count=0,
        cash_values_count=0,
        open_orders_count=0,
        executions_count=0,
        status_nl="ok",
        next_step_nl=None,
        help_nl="ok",
        actions_allowed=False,
        order_submission_allowed=False,
        order_modification_allowed=False,
        order_cancellation_allowed=False,
        suggestions_allowed=False,
        stored_at=_NOW,
    )


def _briefing() -> DailyBriefingRecord:
    return DailyBriefingRecord(
        briefing_id="brief-1",
        briefing_date=date(2025, 5, 24),
        generated_at=_NOW,
        lookback_started_at=_NOW - timedelta(hours=24),
        position_count=2,
        base_currency="USD",
        total_position_value=None,
        cash_total=Decimal("5000"),
        fx_freshness_status="fresh",
        new_suggestion_count=1,
        new_decision_package_count=0,
        new_action_draft_count=0,
        diary_outcomes_closed_count=0,
        critical_event_count=0,
        alert_count=0,
        summary_nl="test",
        help_nl="ok",
        status="ready",
        blocking_reason=None,
    )


def _fake_storage(
    monkeypatch,
    *,
    sync_run=None,
    positions=None,
    cash_snapshots=None,
    saved_briefings=None,
    saved_alerts=None,
    latest_briefing=None,
    latest_alerts=None,
):
    saved_briefings = saved_briefings if saved_briefings is not None else []
    saved_alerts = saved_alerts if saved_alerts is not None else []

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

    class _FakeIbkrRepo:
        def get_latest_ibkr_sync_run(self):
            return sync_run

        def list_ibkr_position_snapshots(self, _run_id: str):
            return list(positions or [])

        def list_ibkr_account_cash_snapshots(self, _run_id: str):
            return list(cash_snapshots or [])

    class _FakeSuggestionRepo:
        def list_latest_asset_suggestions_by_conids(self, _conids):
            return type("_R", (), {"records": ()})()

    class _FakePackageRepo:
        def list_latest_asset_decision_packages_by_conids(self, _conids):
            return type("_R", (), {"records": ()})()

    class _FakeDraftRepo:
        def list_latest_asset_action_drafts_by_conids(self, _conids):
            return type("_R", (), {"records": ()})()

    class _FakeEventRepo:
        def list_asset_action_draft_events(self, _draft_id: str):
            return type("_R", (), {"records": ()})()

    class _FakeDiaryRepo:
        def list_prediction_diary_entries(self, *, limit: int = 200):
            return type("_R", (), {"records": ()})()

    class _FakeBriefingRepo:
        def upsert_daily_briefing(self, record):
            saved_briefings.append(record)

        def save_briefing_alert(self, record):
            saved_alerts.append(record)

        def delete_alerts_for_briefing(self, _briefing_id):
            pass

        def get_latest_daily_briefing(self):
            if latest_briefing is not None:
                return type("_R", (), {"found": True, "record": latest_briefing})()
            return type("_R", (), {"found": False, "record": None})()

        def list_alerts_for_briefing(self, _briefing_id):
            return type("_R", (), {"records": tuple(latest_alerts or [])})()

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
        "SqlAlchemyAssetSuggestionRepository",
        lambda *a, **k: _FakeSuggestionRepo(),
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
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetActionDraftEventRepository",
        lambda *a, **k: _FakeEventRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyPredictionDiaryRepository",
        lambda *a, **k: _FakeDiaryRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyDailyBriefingRepository",
        lambda *a, **k: _FakeBriefingRepo(),
    )
    return saved_briefings, saved_alerts


# ---- POST /briefings/daily/compute ------------------------------------


def test_compute_blocked_when_sync_disabled() -> None:
    r = client.post("/briefings/daily/compute")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "daily_briefing_sync_disabled"
    assert body["safe_for_action_drafts"] is False
    assert body["safe_for_orders"] is False


def test_compute_blocked_when_storage_not_writable() -> None:
    api_settings.daily_briefing_sync_enabled = True
    r = client.post("/briefings/daily/compute")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def test_compute_happy_path_with_no_ibkr_data(monkeypatch) -> None:
    api_settings.daily_briefing_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    saved_briefings, _ = _fake_storage(monkeypatch, sync_run=None)

    r = client.post("/briefings/daily/compute")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "ready"
    assert body["briefing_id"] is not None
    assert body["alert_count"] == 0
    assert body["safe_for_orders"] is False
    assert len(saved_briefings) == 1
    assert saved_briefings[0].position_count == 0


def test_compute_happy_path_with_positions(monkeypatch) -> None:
    api_settings.daily_briefing_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    class _Pos:
        snapshot_id = "p1"
        sync_run_id = "run-1"
        account_ref = "DU"
        conid = "1"
        symbol = "AAPL"
        security_type = "STK"
        currency = "USD"
        exchange = "SMART"
        primary_exchange = "NASDAQ"
        quantity = Decimal("5")
        average_cost = Decimal("150")
        received_at = _NOW
        stored_at = _NOW

    class _Cash:
        snapshot_id = "c1"
        sync_run_id = "run-1"
        account_ref = "DU"
        base_currency = "USD"
        cash = Decimal("3000")
        available_funds = Decimal("3000")
        buying_power = Decimal("3000")
        received_at = _NOW
        stored_at = _NOW

    saved_briefings, _ = _fake_storage(
        monkeypatch,
        sync_run=_sync_run(),
        positions=[_Pos()],
        cash_snapshots=[_Cash()],
    )

    r = client.post("/briefings/daily/compute")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "ready"
    persisted = saved_briefings[0]
    assert persisted.position_count == 1
    assert persisted.cash_total == Decimal("3000")
    assert persisted.base_currency == "USD"


# ---- GET /briefings/daily/latest --------------------------------------


def test_read_returns_not_configured_without_storage() -> None:
    r = client.get("/briefings/daily/latest")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"


def test_read_returns_not_found_when_no_briefing(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch)

    r = client.get("/briefings/daily/latest")
    body = r.json()
    assert body["status"] == "not_found"
    assert body["item"] is None


def test_read_returns_latest_briefing_with_alerts(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    alert = BriefingAlertRecord(
        alert_id="alrt-1",
        briefing_id="brief-1",
        alert_kind="new_suggestion",
        severity="info",
        reference_kind="suggestion",
        reference_id="sug-1",
        title_nl="t",
        body_nl="b",
        acknowledged_at=None,
        linked_at=_NOW,
    )
    _fake_storage(monkeypatch, latest_briefing=_briefing(), latest_alerts=[alert])

    r = client.get("/briefings/daily/latest")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert body["item"]["briefing_id"] == "brief-1"
    assert len(body["item"]["alerts"]) == 1
    assert body["item"]["alerts"][0]["alert_id"] == "alrt-1"
    assert body["item"]["safe_for_orders"] is False
