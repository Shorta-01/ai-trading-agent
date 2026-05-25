"""Endpoint tests for the approve / submit / status routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.ibkr_paper_order_submission_enabled = False
    api_settings.ibkr_paper_order_submission_real_client_enabled = False
    api_settings.ibkr_paper_order_submission_host = None
    api_settings.ibkr_paper_order_submission_port = None
    api_settings.ibkr_paper_order_submission_client_id = None
    api_settings.action_draft_approval_valid_minutes = 5


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _fake_draft(
    *, dry_run_status: str = "passed", account_mode: str = "paper"
) -> object:
    now = datetime(2025, 5, 24, tzinfo=UTC)

    class _Draft:
        draft_id = "draft-1"
        decision_package_id = "dp-1"
        decision_package_content_hash = "hash-1"
        ibkr_conid = "265598"
        symbol = "AAPL"
        currency = "USD"
        exchange = "SMART"
        primary_exchange = "NASDAQ"
        account_mode_attr = account_mode
        expected_account_mode = "paper"
        action_side = "BUY"
        order_type = "LMT"
        tif = "DAY"
        quantity = Decimal("5")
        limit_price = Decimal("180")
        stop_price = None
        trail_amount = None
        trail_percent = None
        bracket_take_profit_limit_price = None
        bracket_stop_loss_price = None
        estimated_order_value = Decimal("900")
        estimated_cash_before = Decimal("10000")
        estimated_cash_after = Decimal("9100")
        estimated_position_quantity_before = Decimal("0")
        estimated_position_quantity_after = Decimal("5")
        estimated_position_value_after = Decimal("900")
        estimated_portfolio_weight_after_pct = Decimal("9.0")
        estimated_concentration_impact_pct = Decimal("9.0")
        orderimpact_base_currency = "USD"
        source_action_label = "Kopen"
        source_action_label_nl = "Kopen"
        status_attr = "dry_run_passed"
        dry_run_status_attr = dry_run_status
        dry_run_failures_json = None
        blocking_reason = None
        rationale_nl = "r"
        explanation_nl = "e"
        created_at = now
        updated_at = now
        safe_for_submission = False
        safe_for_orders = False
        safe_for_broker_submission = False

    draft = _Draft()
    # Mirror "account_mode" / "status" / "dry_run_status" since the
    # orchestrator reads ``draft.account_mode`` / ``status`` directly.
    draft.account_mode = account_mode
    draft.status = "dry_run_passed"
    draft.dry_run_status = dry_run_status
    return draft


def _fake_storage(
    monkeypatch,
    *,
    draft,
    submission_exists: bool = False,
    submission_state: str = "user_approved",
    submission_approved_minutes_ago: int = 1,
    captured_submission: list[object] | None = None,
    captured_events: list[object] | None = None,
):
    saved_submissions = captured_submission if captured_submission is not None else []
    saved_events = captured_events if captured_events is not None else []

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

    class _FakeDraftRepo:
        def get_asset_action_draft_by_id(self, _draft_id: str):
            return type(
                "_Read",
                (),
                {"found": draft is not None, "record": draft},
            )()

    class _FakeSubmissionRepo:
        def __init__(self) -> None:
            now = datetime.now(UTC)
            self._existing = None
            if submission_exists:
                approved_at = now - timedelta(minutes=submission_approved_minutes_ago)

                class _Sub:
                    submission_id = "sub-1"
                    draft_id = "draft-1"
                    state = submission_state
                    approval_status = "approved"
                    approved_at_attr = approved_at
                    approved_by = "owner"
                    approval_dry_run_status = "passed"
                    approval_dry_run_failures_json = None
                    submitted_at = None
                    ibkr_order_id = None
                    ibkr_perm_id = None
                    ibkr_client_id = None
                    ibkr_status_text = None
                    filled_quantity = None
                    remaining_quantity = None
                    average_fill_price = None
                    cancelled_at = None
                    cancellation_reason = None
                    rejected_reason = None
                    reconciled_at = None
                    account_mode = "paper"
                    expected_account_mode = "paper"
                    provider_code = "ibkr"
                    created_at = approved_at
                    updated_at = approved_at
                    last_state_transition_at = approved_at

                sub = _Sub()
                sub.approved_at = approved_at
                self._existing = sub

        def upsert_asset_action_draft_submission(self, record):
            saved_submissions.append(record)
            self._existing = record

        def get_submission_by_draft_id(self, _draft_id: str):
            return type(
                "_Read",
                (),
                {"found": self._existing is not None, "record": self._existing},
            )()

    class _FakeEventRepo:
        def save_asset_action_draft_event(self, record):
            saved_events.append(record)

        def list_asset_action_draft_events(self, _draft_id: str, *, limit: int = 100):
            return type("_List", (), {"records": tuple(saved_events)})()

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
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


# ---- approve endpoint ----------------------------------------------------


def test_approve_blocked_when_storage_not_writable() -> None:
    r = client.post("/action-drafts/foo/approve")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def test_approve_returns_404_when_draft_not_found(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    _fake_storage(monkeypatch, draft=None)

    r = client.post("/action-drafts/missing/approve")
    assert r.status_code == 404


def test_approve_blocks_when_dry_run_failed(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    _fake_storage(monkeypatch, draft=_fake_draft(dry_run_status="failed"))

    r = client.post("/action-drafts/draft-1/approve")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["blocking_reason"] == "dry_run_not_passed"


def test_approve_happy_path_returns_user_approved(monkeypatch) -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.ibkr_expected_environment = "paper"
    _fake_storage(monkeypatch, draft=_fake_draft())

    r = client.post("/action-drafts/draft-1/approve")
    body = r.json()
    assert body["status"] == "approved"
    assert body["state"] == "user_approved"
    assert body["safe_for_broker_submission"] is False


# ---- submit endpoint -----------------------------------------------------


def test_submit_blocked_when_submission_disabled() -> None:
    r = client.post("/action-drafts/foo/submit-to-ibkr-paper")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "ibkr_paper_order_submission_disabled"


def test_submit_blocked_when_real_client_not_built(monkeypatch) -> None:
    api_settings.ibkr_paper_order_submission_enabled = True
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    # real_client_enabled stays False → factory returns None
    monkeypatch.setattr(
        status_routes, "build_real_order_submission_client", lambda _s: None
    )
    r = client.post("/action-drafts/foo/submit-to-ibkr-paper")
    body = r.json()
    assert body["reason"] == "submission_client_unavailable"


def test_submit_happy_path_with_fake_submission_client(monkeypatch) -> None:
    api_settings.ibkr_paper_order_submission_enabled = True
    api_settings.ibkr_paper_order_submission_real_client_enabled = True
    api_settings.ibkr_paper_order_submission_host = "127.0.0.1"
    api_settings.ibkr_paper_order_submission_port = 4002
    api_settings.ibkr_paper_order_submission_client_id = 11
    api_settings.ibkr_sync_account_mode = "paper"
    api_settings.ibkr_expected_environment = "paper"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    _fake_storage(monkeypatch, draft=_fake_draft(), submission_exists=True)

    from portfolio_outlook_api.ibkr_ibapi_order_submission_client import (
        OrderSubmissionResult,
    )

    class _FakeClient:
        def submit(self, _inputs):
            return OrderSubmissionResult(
                accepted=True,
                ibkr_order_id=101,
                ibkr_perm_id=500,
                ibkr_client_id=11,
                ibkr_status_text="Submitted",
                rejected_reason=None,
            )

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        status_routes, "build_real_order_submission_client", lambda _s: _FakeClient()
    )

    r = client.post("/action-drafts/draft-1/submit-to-ibkr-paper")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "submitted"
    assert body["state"] == "awaiting_ibkr_reply"
    assert body["ibkr_order_id"] == 101
    assert body["ibkr_perm_id"] == 500
    assert body["safe_for_broker_submission"] is False
    assert body["safe_for_orders"] is False


# ---- status endpoint -----------------------------------------------------


def test_status_returns_not_configured_without_storage() -> None:
    r = client.get("/action-drafts/draft-1/status")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "not_configured"
    assert body["submission"] is None
    assert body["events"] == []
