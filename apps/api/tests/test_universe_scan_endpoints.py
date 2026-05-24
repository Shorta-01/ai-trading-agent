"""Endpoint tests for the universe-scan routes (Slice 17)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ai_trading_agent_storage import UniverseScanRunRecord
from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_NOW = datetime(2026, 6, 3, 6, 30, tzinfo=UTC)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.universe_scan_sync_enabled = False
    api_settings.eodhd_enabled = False
    api_settings.eodhd_api_key = None


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _scan_run() -> UniverseScanRunRecord:
    return UniverseScanRunRecord(
        run_id="usr-1",
        started_at=_NOW,
        finished_at=_NOW + timedelta(seconds=30),
        status="succeeded",
        triggered_by="manual",
        scanned_count=50,
        persisted_count=48,
        failed_count=2,
        ranked_count=40,
        universe_size=325,
        error_text=None,
    )


def _fake_storage(monkeypatch, *, latest_run=None) -> None:
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

    class _FakeSnapshotRepo:
        def save_snapshot(self, _record):
            pass

    class _FakeScanRepo:
        def save_run(self, _record):
            pass

        def update_run(self, _record):
            pass

        def get_latest_run(self):
            if latest_run is None:
                return type("_R", (), {"found": False, "record": None})()
            return type("_R", (), {"found": True, "record": latest_run})()

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetFundamentalsSnapshotRepository",
        lambda *a, **k: _FakeSnapshotRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyUniverseScanRunRepository",
        lambda *a, **k: _FakeScanRepo(),
    )


# ---- POST /universe/scan/run ------------------------------------------


def test_scan_blocked_when_sync_disabled() -> None:
    r = client.post("/universe/scan/run")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "universe_scan_sync_disabled"
    assert body["safe_for_orders"] is False


def test_scan_blocked_when_eodhd_not_configured() -> None:
    api_settings.universe_scan_sync_enabled = True
    r = client.post("/universe/scan/run")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "eodhd_not_configured"


def test_scan_blocked_when_storage_not_writable() -> None:
    api_settings.universe_scan_sync_enabled = True
    api_settings.eodhd_enabled = True
    api_settings.eodhd_api_key = "test-key"
    r = client.post("/universe/scan/run")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def test_scan_happy_path_runs_orchestrator(monkeypatch) -> None:
    api_settings.universe_scan_sync_enabled = True
    api_settings.eodhd_enabled = True
    api_settings.eodhd_api_key = "test-key"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.universe_scan_max_tickers_per_run = 2
    _fake_storage(monkeypatch)

    # Monkey-patch the EODHD client construction to keep tests offline.
    from portfolio_outlook_api import eodhd_client as ec
    from portfolio_outlook_api import universe_scan_sync as scan_module

    class _StubReport:
        run_id = "usr-stub"
        requested_at = _NOW
        completed_at = _NOW + timedelta(seconds=10)
        status = "succeeded"
        status_nl = "ok"
        help_nl = "ok"
        universe_size = 325
        scanned_count = 2
        persisted_count = 2
        failed_count = 0
        ranked_count = 2
        blocking_reason = None
        failures: tuple = ()

    monkeypatch.setattr(ec.EodhdClient, "__init__", lambda self, *a, **k: None)
    monkeypatch.setattr(scan_module, "scan_universe", lambda **kwargs: _StubReport())

    r = client.post("/universe/scan/run")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "succeeded"
    assert body["run_id"] == "usr-stub"
    assert body["scanned_count"] == 2
    assert body["safe_for_orders"] is False


# ---- GET /universe/scan/runs/latest -----------------------------------


def test_latest_returns_not_configured_without_storage() -> None:
    r = client.get("/universe/scan/runs/latest")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"


def test_latest_returns_not_found_when_no_runs(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch)
    r = client.get("/universe/scan/runs/latest")
    body = r.json()
    assert body["status"] == "not_found"


def test_latest_returns_run_when_present(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(monkeypatch, latest_run=_scan_run())
    r = client.get("/universe/scan/runs/latest")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert body["item"]["run_id"] == "usr-1"
    assert body["item"]["scanned_count"] == 50
    assert body["item"]["persisted_count"] == 48
    assert body["item"]["ranked_count"] == 40
    assert body["safe_for_orders"] is False
