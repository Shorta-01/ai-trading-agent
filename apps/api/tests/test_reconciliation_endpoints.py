"""Endpoint tests for /action-drafts/reconcile (Slice 8)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetActionDraftSubmissionRecord,
    IbkrExecutionSnapshotRecord,
    IbkrSyncRunRecord,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_NOW = datetime(2025, 5, 24, 12, 0, tzinfo=UTC)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.reconciliation_sync_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _fake_sync_run() -> IbkrSyncRunRecord:
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
        positions_count=1,
        cash_values_count=1,
        open_orders_count=1,
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


def _fake_submission(
    *, state: str = "working"
) -> AssetActionDraftSubmissionRecord:
    return AssetActionDraftSubmissionRecord(
        submission_id="sub-1",
        draft_id="draft-1",
        state=state,
        approval_status="user_approved",
        approved_at=_NOW - timedelta(minutes=5),
        approved_by="user@example.com",
        approval_dry_run_status="passed",
        approval_dry_run_failures_json=None,
        submitted_at=_NOW - timedelta(minutes=3),
        ibkr_order_id=555,
        ibkr_perm_id=999,
        ibkr_client_id=42,
        ibkr_status_text="Submitted",
        filled_quantity=None,
        remaining_quantity=None,
        average_fill_price=None,
        cancelled_at=None,
        cancellation_reason=None,
        rejected_reason=None,
        reconciled_at=None,
        account_mode="paper",
        expected_account_mode="paper",
        provider_code="ibkr",
        created_at=_NOW - timedelta(minutes=5),
        updated_at=_NOW - timedelta(minutes=3),
        last_state_transition_at=_NOW - timedelta(minutes=3),
    )


def _fake_execution() -> IbkrExecutionSnapshotRecord:
    return IbkrExecutionSnapshotRecord(
        snapshot_id="ex-1",
        sync_run_id="run-1",
        account_ref="DU000001",
        execution_id="exec-1",
        ibkr_order_id=555,
        ibkr_perm_id=999,
        symbol="AAPL",
        security_type="STK",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        side="BUY",
        quantity=Decimal("5"),
        price=Decimal("180"),
        execution_time=_NOW,
        commission=Decimal("1.0"),
        commission_currency="USD",
        realized_pnl=None,
        raw_execution_reference=None,
        received_at=_NOW,
        stored_at=_NOW,
    )


def _fake_storage(
    monkeypatch,
    *,
    sync_run=None,
    positions=None,
    submissions=None,
    open_orders=None,
    executions=None,
    drafts=None,
):
    saved_submissions: list = []
    saved_events: list = []

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

    class _Pos:
        def __init__(self, conid: str) -> None:
            self.conid = conid

    class _FakeIbkrRepo:
        def get_latest_ibkr_sync_run(self):
            return sync_run

        def list_ibkr_position_snapshots(self, _run_id: str):
            return list(positions or [])

        def list_ibkr_open_order_snapshots(self, _run_id: str):
            return list(open_orders or [])

        def list_ibkr_execution_snapshots(self, _run_id: str):
            return list(executions or [])

    class _FakeDraftRepo:
        def list_latest_asset_action_drafts_by_conids(self, _conids):
            return type("_R", (), {"records": tuple(drafts or [])})()

    class _FakeSubmissionRepo:
        def get_submission_by_draft_id(self, draft_id: str):
            for s in submissions or []:
                if s.draft_id == draft_id:
                    return type("_R", (), {"found": True, "record": s})()
            return type("_R", (), {"found": False, "record": None})()

        def upsert_asset_action_draft_submission(self, record):
            saved_submissions.append(record)

    class _FakeEventRepo:
        def save_asset_action_draft_event(self, record):
            saved_events.append(record)

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
        "SqlAlchemyAssetActionDraftRepository",
        lambda *a, **k: _FakeDraftRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetActionDraftSubmissionRepository",
        lambda *a, **k: _FakeSubmissionRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetActionDraftEventRepository",
        lambda *a, **k: _FakeEventRepo(),
    )
    return saved_submissions, saved_events


def test_reconcile_blocked_when_sync_disabled() -> None:
    r = client.post("/action-drafts/reconcile")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "reconciliation_sync_disabled"
    assert body["safe_for_orders"] is False
    assert body["safe_for_broker_submission"] is False


def test_reconcile_blocked_when_storage_not_writable() -> None:
    api_settings.reconciliation_sync_enabled = True
    r = client.post("/action-drafts/reconcile")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def test_reconcile_blocked_when_no_ibkr_sync_run(monkeypatch) -> None:
    api_settings.reconciliation_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    _fake_storage(monkeypatch, sync_run=None)

    r = client.post("/action-drafts/reconcile")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "no_ibkr_sync_run"


def test_reconcile_happy_path_fills_and_reconciles(monkeypatch) -> None:
    api_settings.reconciliation_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    class _Pos:
        conid = "265598"

    class _Draft:
        draft_id = "draft-1"
        quantity = Decimal("5")

    saved_submissions, saved_events = _fake_storage(
        monkeypatch,
        sync_run=_fake_sync_run(),
        positions=[_Pos()],
        submissions=[_fake_submission()],
        open_orders=[],
        executions=[_fake_execution()],
        drafts=[_Draft()],
    )

    r = client.post("/action-drafts/reconcile")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "completed"
    assert body["submissions_total"] == 1
    assert body["submissions_filled"] == 1
    assert body["safe_for_orders"] is False
    assert body["safe_for_broker_submission"] is False
    # filled then reconciled
    assert len(saved_submissions) == 2
    assert saved_submissions[1].state == "reconciled"


def test_reconcile_empty_pool_returns_completed_with_zero(monkeypatch) -> None:
    api_settings.reconciliation_sync_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    _fake_storage(
        monkeypatch,
        sync_run=_fake_sync_run(),
        positions=[],
        submissions=[],
        open_orders=[],
        executions=[],
        drafts=[],
    )

    r = client.post("/action-drafts/reconcile")
    body = r.json()
    assert body["status"] == "completed"
    assert body["submissions_total"] == 0
    assert body["submissions_filled"] == 0
