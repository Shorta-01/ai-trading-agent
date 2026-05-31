"""Endpoint tests for ``GET /digests/today``."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from portfolio_outlook_api import digest_routes
from portfolio_outlook_api.digest_routes import settings as api_settings
from portfolio_outlook_api.main import app

client = TestClient(app)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def test_returns_not_configured_when_storage_disabled() -> None:
    r = client.get("/digests/today")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "not_configured"
    assert body["alerts"] == []
    assert body["safe_for_orders"] is False


def _fake_storage(monkeypatch, *, latest_run, positions, digest_record):
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

    class _FakeIbkr:
        def get_latest_ibkr_sync_run(self):
            return latest_run

        def list_ibkr_position_snapshots(self, _id: str):
            return positions

    class _DigestResult:
        def __init__(self, record):
            self.found = record is not None
            self.record = record

    class _FakeDigestRepo:
        def get_latest_daily_digest_for_account(self, _ref: str):
            return _DigestResult(digest_record)

    monkeypatch.setattr(
        digest_routes, "StorageConnectionProvider", _FakeStorageProvider
    )
    monkeypatch.setattr(
        digest_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        digest_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: _FakeIbkr(),
    )
    monkeypatch.setattr(
        digest_routes,
        "SqlAlchemyDailyDigestRepository",
        lambda *a, **k: _FakeDigestRepo(),
    )


def test_returns_no_ibkr_sync_when_no_run_yet(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    _fake_storage(
        monkeypatch, latest_run=None, positions=[], digest_record=None
    )
    r = client.get("/digests/today")
    body = r.json()
    assert body["status"] == "no_ibkr_sync_run"


def test_returns_no_digest_when_no_record_for_account(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"

    class _Run:
        sync_run_id = "ibkr-x"

    class _Pos:
        account_ref = "DU1234567"

    _fake_storage(
        monkeypatch,
        latest_run=_Run(),
        positions=[_Pos()],
        digest_record=None,
    )
    r = client.get("/digests/today")
    body = r.json()
    assert body["status"] == "no_digest"


def test_returns_digest_payload_when_present(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"

    class _Run:
        sync_run_id = "ibkr-x"

    class _Pos:
        account_ref = "DU1234567"

    class _Digest:
        digest_id = "digest-x"
        ibkr_account_ref = "DU1234567"
        market_code = "EURONEXT"
        briefing_date = date(2026, 5, 31)
        generated_at = datetime(2026, 5, 31, 17, 45, tzinfo=UTC)
        nav_summary_json = {
            "total_nav": "100000.00",
            "delta_pct": "-0.50",
            "currency": "EUR",
            "computed_from": "nav_snapshots",
        }
        positions_summary_json = {
            "position_count": 3,
            "top_winners": [],
            "top_losers": [],
            "by_currency": {"EUR": 3},
        }
        suggestions_summary_json = {
            "total": 5,
            "by_action_label": {"Houden": 4, "Bekijken": 1},
            "high_confidence_count": 0,
            "new_today": 5,
        }
        action_drafts_summary_json = {
            "created_today": 0,
            "approved_today": 0,
            "submitted_today": 0,
            "cancelled_today": 0,
            "by_state": {},
        }
        alerts_json = [
            {
                "kind": "nav_drop",
                "severity_nl": "Waarschuwing",
                "title_nl": "NAV is vandaag -0.50% gedaald",
                "body_nl": "Test body.",
                "reference_kind": "nav",
                "reference_id": None,
            }
        ]
        status = "ready"
        blocking_reason = None

    _fake_storage(
        monkeypatch,
        latest_run=_Run(),
        positions=[_Pos()],
        digest_record=_Digest(),
    )
    r = client.get("/digests/today")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ready"
    assert body["market_code"] == "EURONEXT"
    assert body["briefing_date"] == "2026-05-31"
    assert body["nav_summary"]["delta_pct"] == "-0.50"
    assert body["suggestions_summary"]["total"] == 5
    assert len(body["alerts"]) == 1
    assert body["alerts"][0]["kind"] == "nav_drop"
    assert body["safe_for_orders"] is False
