"""Endpoint tests for ``GET /portfolio/nav/history``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import IbkrNavSnapshotRecord
from fastapi.testclient import TestClient

from portfolio_outlook_api import portfolio_nav_history_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

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


def _record(
    *, recorded_at: datetime, nav_value: Decimal, currency: str = "EUR"
) -> IbkrNavSnapshotRecord:
    return IbkrNavSnapshotRecord(
        snapshot_id=f"nav-{int(recorded_at.timestamp())}",
        ibkr_account_id="DU1234567",
        base_currency=currency,
        nav_value=nav_value,
        recorded_at=recorded_at,
        stored_at=recorded_at,
    )


def _install_fake_storage(monkeypatch, *, records: list[IbkrNavSnapshotRecord]) -> None:
    class _Checked:
        connection = object()
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Checked()

        def __exit__(self, *_):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    class _FakeRepo:
        def list_ibkr_nav_snapshots_since(
            self, *, ibkr_account_id: str, since: datetime
        ):
            # Mirror the real repo: filter by since, return oldest first.
            filtered = [r for r in records if r.recorded_at >= since]
            return sorted(filtered, key=lambda r: r.recorded_at)

    monkeypatch.setattr(
        portfolio_nav_history_routes,
        "StorageConnectionProvider",
        _FakeStorageProvider,
    )
    monkeypatch.setattr(
        portfolio_nav_history_routes,
        "build_database_connection_settings",
        lambda _u: object(),
    )
    monkeypatch.setattr(
        portfolio_nav_history_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: _FakeRepo(),
    )


def test_returns_no_account_when_no_hint_configured() -> None:
    r = client.get("/portfolio/nav/history")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "no_account_configured"
    assert body["points"] == []


def test_returns_not_configured_when_storage_disabled() -> None:
    api_settings.ibkr_account_id_hint = "DU1234567"
    r = client.get("/portfolio/nav/history")
    body = r.json()
    assert body["status"] == "not_configured"


def test_returns_oldest_first_points_within_window(monkeypatch) -> None:
    api_settings.ibkr_account_id_hint = "DU1234567"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    now = datetime.now(UTC)
    records = [
        _record(
            recorded_at=now - timedelta(days=20),
            nav_value=Decimal("100000"),
        ),
        _record(
            recorded_at=now - timedelta(days=10),
            nav_value=Decimal("100500"),
        ),
        _record(recorded_at=now, nav_value=Decimal("101000")),
    ]
    _install_fake_storage(monkeypatch, records=records)
    r = client.get("/portfolio/nav/history?days=30")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert body["ibkr_account_id"] == "DU1234567"
    assert body["base_currency"] == "EUR"
    assert body["days_requested"] == 30
    assert len(body["points"]) == 3
    # Oldest first, latest at the end.
    assert body["points"][0]["nav_value"] == "100000"
    assert body["points"][-1]["nav_value"] == "101000"


def test_excludes_points_older_than_the_requested_window(monkeypatch) -> None:
    api_settings.ibkr_account_id_hint = "DU1234567"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    now = datetime.now(UTC)
    records = [
        _record(
            recorded_at=now - timedelta(days=100),  # outside 30-day window
            nav_value=Decimal("90000"),
        ),
        _record(
            recorded_at=now - timedelta(days=5),
            nav_value=Decimal("100500"),
        ),
    ]
    _install_fake_storage(monkeypatch, records=records)
    body = client.get("/portfolio/nav/history?days=30").json()
    assert len(body["points"]) == 1
    assert body["points"][0]["nav_value"] == "100500"


def test_returns_no_points_when_period_is_empty(monkeypatch) -> None:
    api_settings.ibkr_account_id_hint = "DU1234567"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _install_fake_storage(monkeypatch, records=[])
    body = client.get("/portfolio/nav/history").json()
    assert body["status"] == "no_points"
    assert body["points"] == []
    assert body["base_currency"] is None


def test_days_parameter_is_clamped_via_pydantic() -> None:
    api_settings.ibkr_account_id_hint = "DU1234567"
    r = client.get("/portfolio/nav/history?days=0")
    assert r.status_code == 422
    r = client.get("/portfolio/nav/history?days=9999")
    assert r.status_code == 422
